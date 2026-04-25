#!/usr/bin/env bash
# Bulk LC Validation smoke — Phase A1 part 2.
#
# Spins up a customer_lc_validation bulk job with 5 LC packages from
# the importer corpus, kicks the worker, then polls the job until
# terminal and prints the per-item verdict summary.
#
# Run AFTER:
#   1. Backend deployed to Render (apps/api).
#   2. Migration applied manually:
#        render jobs create srv-d41dio8dl3ps73db8gpg \
#          --start-command "alembic upgrade head"
#   3. /health/db-schema confirms bulk_jobs/bulk_items tables exist.
#
# Usage:  bash scripts/smoke_bulk_validate.sh

set -u

API="${API:-https://api.trdrhub.com}"
SUPABASE="https://nnmmhgnriisfsncphipd.supabase.co"
ANON_KEY="sb_publishable_db40L4wNiQX0jOTCRJi-8g_9p-PWmN3"
EMAIL="${SMOKE_EMAIL:-imran@iec.com}"
PASSWORD="${SMOKE_PASSWORD:-ripc0722}"

T="${LOCALAPPDATA:-$HOME}/Temp"
mkdir -p "$T" 2>/dev/null || true
AUTH="$T/smoke_bulk_auth.json"
COOK="$T/smoke_bulk_cookies.txt"
CSRF_JSON="$T/smoke_bulk_csrf.json"
CREATE_OUT="$T/smoke_bulk_create.json"
ITEM_OUT="$T/smoke_bulk_item.json"
JOB_OUT="$T/smoke_bulk_job.json"

# Five LC packages we'll upload — use the existing importer corpus to
# avoid creating new fixture data. Each subdir under SHIPMENT_CLEAN
# becomes one bulk item.
FIX_BASE="apps/web/tests/fixtures/importer-corpus"
LC_DIRS=(
  "US-VN/SHIPMENT_CLEAN"
  "UK-IN/SHIPMENT_CLEAN"
  "DE-CN/SHIPMENT_CLEAN"
  "BD-CN/SHIPMENT_CLEAN"
  "US-VN/DRAFT_CLEAN"
)

rm -f "$AUTH" "$COOK" "$CSRF_JSON" "$CREATE_OUT" "$ITEM_OUT" "$JOB_OUT"

echo "=== 1. Auth ==="
curl -s -X POST "$SUPABASE/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  -o "$AUTH"
TOKEN=$(python -c "import json; print(json.load(open(r'$AUTH'))['access_token'])")
echo "  token: ${TOKEN:0:28}..."

echo ""
echo "=== 2. CSRF ==="
curl -s -c "$COOK" "$API/auth/csrf-token" > "$CSRF_JSON"
CSRF=$(python -c "import json; print(json.load(open(r'$CSRF_JSON'))['csrf_token'])")
echo "  csrf: ${CSRF:0:28}..."

echo ""
echo "=== 3. Create bulk job ==="
curl -s -b "$COOK" -c "$COOK" -o "$CREATE_OUT" \
  -X POST "$API/api/bulk-validate/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-CSRF-Token: $CSRF" \
  -H "Content-Type: application/json" \
  -d '{"name":"smoke-bulk-5lc","description":"Phase A1.2 smoke","concurrency":2}'
JOB_ID=$(python -c "import json; print(json.load(open(r'$CREATE_OUT'))['job_id'])")
echo "  job_id: $JOB_ID"

echo ""
echo "=== 4. Upload 5 items ==="
for dir in "${LC_DIRS[@]}"; do
  pkg_path="$FIX_BASE/$dir"
  lc_id="${dir//\//-}"
  if [ ! -d "$pkg_path" ]; then
    echo "  SKIP $lc_id — missing dir $pkg_path"
    continue
  fi
  # Build curl -F args for every PDF in the directory.
  pdf_args=()
  shopt -s nullglob
  for pdf in "$pkg_path"/*.pdf; do
    pdf_args+=( -F "files=@$pdf" )
  done
  shopt -u nullglob
  if [ "${#pdf_args[@]}" -eq 0 ]; then
    echo "  SKIP $lc_id — no PDFs found"
    continue
  fi
  HTTP=$(curl -s -b "$COOK" -c "$COOK" -o "$ITEM_OUT" \
    -w "%{http_code}" \
    -X POST "$API/api/bulk-validate/$JOB_ID/items" \
    -H "Authorization: Bearer $TOKEN" \
    -H "X-CSRF-Token: $CSRF" \
    -F "lc_identifier=$lc_id" \
    "${pdf_args[@]}")
  echo "  $lc_id → HTTP $HTTP, ${#pdf_args[@]} files"
done

echo ""
echo "=== 5. Run job ==="
curl -s -b "$COOK" -c "$COOK" \
  -X POST "$API/api/bulk-validate/$JOB_ID/run" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-CSRF-Token: $CSRF" \
  -H "Content-Type: application/json" -d '{}' | python -m json.tool

echo ""
echo "=== 6. Poll job until terminal (max 30 min) ==="
for i in $(seq 1 360); do  # 360 * 5s = 30 min
  curl -s -b "$COOK" -c "$COOK" -o "$JOB_OUT" \
    "$API/api/bulk-validate/$JOB_ID" \
    -H "Authorization: Bearer $TOKEN"
  STATUS=$(python -c "import json; print(json.load(open(r'$JOB_OUT'))['status'])")
  PROC=$(python -c "import json; d=json.load(open(r'$JOB_OUT')); print(f\"{d['succeeded_items']}✓/{d['failed_items']}✗/{d['skipped_items']}⤬ of {d['total_items']}\")")
  echo "  [t+$((i*5))s] status=$STATUS  $PROC"
  case "$STATUS" in
    succeeded|failed|partial|cancelled) break ;;
  esac
  sleep 5
done

echo ""
echo "=== 7. Per-item summary ==="
python <<PY
import json
d = json.load(open(r"$JOB_OUT"))
print(f"  Job status: {d['status']}")
print(f"  Items: {d['succeeded_items']}✓ / {d['failed_items']}✗ / {d['skipped_items']}⤬ of {d['total_items']}")
print(f"  Duration: {d.get('duration_seconds') or '?'}s")
print()
for it in d.get("items", []):
    summary = it.get("result_summary") or {}
    err = it.get("last_error") or ""
    print(f"  - {it['lc_identifier']:<30} {it['status']:<10} ", end="")
    if summary:
        print(f"verdict={summary.get('verdict')!r} score={summary.get('compliance_score')!r} findings={summary.get('finding_count')!r}")
    elif err:
        print(f"ERROR: {err[:100]}")
    else:
        print()
PY

echo ""
echo "Artifacts: $T/smoke_bulk_*.json"
