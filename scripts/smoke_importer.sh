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

FIX="apps/web/tests/fixtures/importer-corpus/US-VN"

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
echo "   uploading US-VN/DRAFT_CLEAN/LC.pdf, extract_only=true"
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
python <<PY
import json
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
if d.get("documents"):
    doc0 = d["documents"][0]
    print("     doc[0] type:", doc0.get("document_type"))
    fields = doc0.get("extracted_fields") or {}
    # Key MT700 fields that should be extracted
    for k in ("lc_number","applicant_name","beneficiary_name","currency","amount","port_of_loading","port_of_discharge","latest_shipment_date"):
        v = fields.get(k)
        if v is not None:
            print(f"     {k}: {v}")
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
echo "   uploading US-VN/SHIPMENT_CLEAN/* (7 files)"
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
  -F "files=@$FIX/SHIPMENT_CLEAN/LC.pdf" \
  -F "files=@$FIX/SHIPMENT_CLEAN/Invoice.pdf" \
  -F "files=@$FIX/SHIPMENT_CLEAN/Bill_of_Lading.pdf" \
  -F "files=@$FIX/SHIPMENT_CLEAN/Packing_List.pdf" \
  -F "files=@$FIX/SHIPMENT_CLEAN/Certificate_of_Origin.pdf" \
  -F "files=@$FIX/SHIPMENT_CLEAN/Insurance_Certificate.pdf" \
  -F "files=@$FIX/SHIPMENT_CLEAN/Inspection_Certificate.pdf")
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
echo "Artifacts saved under: $T/smoke_*.json"
