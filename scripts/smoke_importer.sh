#!/usr/bin/env bash
# Importer-side smoke test. Exercises the full live pipeline for both moments:
#   Moment 1 — Draft LC Review (workflow_type=importer_draft_lc)
#   Moment 2 — Supplier Doc Review (workflow_type=importer_supplier_docs)
#
# Uses the US-VN corridor from apps/web/tests/fixtures/importer-corpus/ so
# no Bangladesh-specific data is in the test path.
#
# Requires: curl, python, jq-ish parsing via python.

set -u

API="${API:-https://api.trdrhub.com}"
SUPABASE="https://nnmmhgnriisfsncphipd.supabase.co"
ANON_KEY="sb_publishable_db40L4wNiQX0jOTCRJi-8g_9p-PWmN3"
EMAIL="${SMOKE_EMAIL:-imran@iec.com}"
PASSWORD="${SMOKE_PASSWORD:-ripc0722}"
CORRIDOR="${CORRIDOR:-US-VN}"

# Temp paths — use a real Windows-native path so both MSYS curl and
# Windows-native python can read/write. On Git-Bash, $TEMP is /tmp which
# curl can use but python can't resolve.
T="${LOCALAPPDATA:-$HOME}/Temp"
mkdir -p "$T" 2>/dev/null || true
AUTH="$T/smoke_auth.json"
COOK="$T/smoke_cookies.txt"
CSRF_JSON="$T/smoke_csrf.json"
EX1="$T/smoke_ex_draft.json"
RES1="$T/smoke_res_draft.json"
EX2="$T/smoke_ex_supplier.json"
RES2="$T/smoke_res_supplier.json"

FIX="apps/web/tests/fixtures/importer-corpus/$CORRIDOR"

rm -f "$AUTH" "$COOK" "$EX1" "$RES1" "$EX2" "$RES2"

echo "=== 1. Auth via Supabase password grant ==="
curl -s -X POST "$SUPABASE/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  -o "$AUTH"
TOKEN=$(python -c "import json; print(json.load(open(r'$AUTH'))['access_token'])")
echo "  token acquired: ${TOKEN:0:28}..."

echo ""
echo "=== 2. CSRF token ==="
curl -s -c "$COOK" "$API/auth/csrf-token" > "$CSRF_JSON"
CSRF=$(python -c "import json; print(json.load(open(r'$T/smoke_csrf.json'))['csrf_token'])")
echo "  csrf acquired: ${CSRF:0:28}..."

echo ""
echo "=== 3. Moment 1 — Draft LC (workflow_type=importer_draft_lc) ==="
echo "   uploading $CORRIDOR/DRAFT_CLEAN/LC.pdf, extract_only=true"
HTTP1=$(curl -s -b "$COOK" -c "$COOK" -o "$EX1" \
  -w "%{http_code}|%{time_total}" \
  --max-time 300 \
  -X POST "$API/api/validate/?workflow_type=importer_draft_lc" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-CSRF-Token: $CSRF" \
  -F "extract_only=true" \
  -F "document_type=letter_of_credit" \
  -F "files=@$FIX/DRAFT_CLEAN/LC.pdf")
echo "   extract HTTP $HTTP1"
SEMANTIC_FAILS_FILE="$T/smoke_semantic_fails.txt"
: > "$SEMANTIC_FAILS_FILE"
python <<PY
import json, os, sys
from decimal import Decimal
sys.path.insert(0, "scripts")
try:
    d = json.load(open(r"$EX1"))
except Exception as e:
    print("   ERROR parsing extract response:", e)
    print("   first 500 bytes of response:", open(r"$EX1").read()[:500])
    raise SystemExit(1)
print("   status:", d.get("status"))
print("   job_id:", d.get("job_id"))
print("   workflow_type:", d.get("workflow_type"))
print("   documents:", len(d.get("documents", [])))

# ---- Semantic diff: verify extracted LC fields against corridor truth -----
fails = 0
if d.get("documents"):
    doc0 = d["documents"][0]
    print("     doc[0] type:", doc0.get("document_type"))
    fields = doc0.get("extracted_fields") or {}
    try:
        from importer_corpus.corridors import get_corridor
        c = get_corridor("$CORRIDOR")
    except Exception as e:
        print(f"   WARN: could not load corridor truth: {e}")
        c = None
    if c is not None:
        # Expected -> extracted-key mapping. Amount derives from goods_line_items.
        line_sum = sum(Decimal(str(i["qty"])) * Decimal(str(i["unit_price"]))
                       for i in c.get("goods_line_items") or [])
        expected = {
            "lc_number": c["lc_number"],
            "currency": c["currency"],
            "amount": float(line_sum),
            "port_of_loading": c["port_loading"],
            "port_of_discharge": c["port_discharge"],
        }
        print("   --- semantic diff (extracted vs corridor truth) ---")
        for k, exp in expected.items():
            got = fields.get(k)
            if got is None:
                print(f"     [FAIL] {k}: MISSING (expected {exp!r})")
                fails += 1
                continue
            # Numeric tolerance for amount; substring tolerance for ports
            # (extractor may keep the canonical 'PORT, COUNTRY' suffix that
            # the corpus value also uses, so direct equality usually works)
            ok = False
            if k == "amount":
                try:
                    ok = abs(float(got) - float(exp)) < 0.01
                except (TypeError, ValueError):
                    ok = False
            elif k in ("port_of_loading", "port_of_discharge"):
                ok = (str(exp).strip().upper() in str(got).strip().upper()) or \
                     (str(got).strip().upper() in str(exp).strip().upper())
            else:
                ok = str(got).strip() == str(exp).strip()
            flag = "OK  " if ok else "FAIL"
            print(f"     [{flag}] {k}: got={got!r}  expected={exp!r}")
            if not ok:
                fails += 1
print(f"   semantic-diff fails: {fails}")
# Persist for the bash summary at the end
with open(r"$SEMANTIC_FAILS_FILE", "a") as f:
    f.write(f"M1 {fails}\n")
PY

JOB1=$(python -c "import json; print(json.load(open(r'$EX1')).get('job_id',''))")
if [ -z "$JOB1" ]; then
  echo "   ERROR: no job_id — skipping resume"
else
  echo "   resuming for validation…"
  HTTP1R=$(curl -s -b "$COOK" -c "$COOK" -o "$RES1" \
    -w "%{http_code}|%{time_total}" \
    --max-time 300 \
    -X POST "$API/api/validate/resume/$JOB1" \
    -H "Authorization: Bearer $TOKEN" \
    -H "X-CSRF-Token: $CSRF" \
    -H "Content-Type: application/json" \
    -d '{"field_overrides": {}}')
  echo "   resume HTTP $HTTP1R"
  python <<PY
import json
try:
    d = json.load(open(r"$RES1"))
except Exception as e:
    print("   ERROR parsing resume response:", e)
    raise SystemExit(1)
print("   workflow_type (response):", d.get("workflow_type"))
sr = d.get("structured_result") or {}
issues = d.get("issues") or sr.get("issues") or []
print("   issues:", len(issues))
if issues:
    for i, x in enumerate(issues[:5], 1):
        sev = (x or {}).get("severity", "?")
        title = (x or {}).get("title") or (x or {}).get("message") or (x or {}).get("finding") or ""
        print(f"     [{i}] {sev}: {title[:110]}")
bv = d.get("bank_verdict") or sr.get("bank_verdict") or {}
if bv:
    print("   verdict:", bv.get("overall_verdict"))
    summ = bv.get("issue_summary") or {}
    print("   summary:", summ)
PY
fi

echo ""
echo "=== 4. Moment 2 — Supplier Docs (workflow_type=importer_supplier_docs) ==="
# Glob every PDF in the corridor's SHIPMENT_CLEAN directory so newly-added
# docs (Beneficiary_Certificate, Fumigation_Certificate, Draft_BoE, etc.)
# get picked up automatically — no need to keep this list in sync.
SHIPMENT_DIR="$FIX/SHIPMENT_CLEAN"
M2_FILE_ARGS=()
shopt -s nullglob
for pdf in "$SHIPMENT_DIR"/*.pdf; do
  M2_FILE_ARGS+=( -F "files=@$pdf" )
done
shopt -u nullglob
echo "   uploading $CORRIDOR/SHIPMENT_CLEAN/*.pdf (${#M2_FILE_ARGS[@]} curl args / $((${#M2_FILE_ARGS[@]}/2)) files)"
# Re-grab CSRF in case state drifted
curl -s -c "$COOK" "$API/auth/csrf-token" > "$CSRF_JSON"
CSRF=$(python -c "import json; print(json.load(open(r'$T/smoke_csrf.json'))['csrf_token'])")

HTTP2=$(curl -s -b "$COOK" -c "$COOK" -o "$EX2" \
  -w "%{http_code}|%{time_total}" \
  --max-time 600 \
  -X POST "$API/api/validate/?workflow_type=importer_supplier_docs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-CSRF-Token: $CSRF" \
  -F "extract_only=true" \
  -F "document_type=letter_of_credit" \
  "${M2_FILE_ARGS[@]}")
echo "   extract HTTP $HTTP2"
python <<PY
import json
try:
    d = json.load(open(r"$EX2"))
except Exception as e:
    print("   ERROR parsing extract response:", e)
    print("   first 500 bytes of response:", open(r"$EX2").read()[:500])
    raise SystemExit(1)
print("   status:", d.get("status"))
print("   job_id:", d.get("job_id"))
print("   workflow_type:", d.get("workflow_type"))
print("   documents:", len(d.get("documents", [])))
for doc in d.get("documents", []):
    t = doc.get("document_type","?")
    fn = doc.get("filename") or doc.get("original_filename") or ""
    print(f"     - {t}: {fn}")
PY

JOB2=$(python -c "import json; print(json.load(open(r'$EX2')).get('job_id',''))")
if [ -z "$JOB2" ]; then
  echo "   ERROR: no job_id — skipping resume"
else
  echo "   resuming for validation…"
  HTTP2R=$(curl -s -b "$COOK" -c "$COOK" -o "$RES2" \
    -w "%{http_code}|%{time_total}" \
    --max-time 600 \
    -X POST "$API/api/validate/resume/$JOB2" \
    -H "Authorization: Bearer $TOKEN" \
    -H "X-CSRF-Token: $CSRF" \
    -H "Content-Type: application/json" \
    -d '{"field_overrides": {}}')
  echo "   resume HTTP $HTTP2R"
  python <<PY
import json
try:
    d = json.load(open(r"$RES2"))
except Exception as e:
    print("   ERROR parsing resume response:", e)
    raise SystemExit(1)
print("   workflow_type (response):", d.get("workflow_type"))
sr = d.get("structured_result") or {}
issues = d.get("issues") or sr.get("issues") or []
print("   issues:", len(issues))
if issues:
    sev_counts = {}
    for x in issues:
        sev_counts[(x or {}).get("severity","?")] = sev_counts.get((x or {}).get("severity","?"),0)+1
    print("   severity breakdown:", sev_counts)
    for i, x in enumerate(issues[:10], 1):
        sev = (x or {}).get("severity", "?")
        title = (x or {}).get("title") or (x or {}).get("message") or (x or {}).get("finding") or ""
        print(f"     [{i}] {sev}: {title[:110]}")
bv = d.get("bank_verdict") or sr.get("bank_verdict") or {}
if bv:
    print("   verdict:", bv.get("overall_verdict"))
    summ = bv.get("issue_summary") or {}
    print("   summary:", summ)
PY
fi

echo ""
echo "=== 5. Summary ==="
echo "  extract1=$HTTP1  resume1=${HTTP1R:-SKIPPED}"
echo "  extract2=$HTTP2  resume2=${HTTP2R:-SKIPPED}"
SEM_FAIL_TOTAL=0
if [ -f "$SEMANTIC_FAILS_FILE" ]; then
  SEM_FAIL_TOTAL=$(awk '{sum += $2} END {print sum+0}' "$SEMANTIC_FAILS_FILE")
fi
echo "  semantic-diff fails (LC fields vs corridor truth): $SEM_FAIL_TOTAL"
echo "Artifacts saved under: $T/smoke_*.json"
# Exit non-zero on any semantic failure so CI / the smoke matrix sees red.
if [ "$SEM_FAIL_TOTAL" -gt 0 ]; then
  exit 1
fi
