import os
import sys
from pathlib import Path
import shutil

sys.path.append('tools/day3_pipeline')
from day3_pipeline_core import read_csv, bootstrap_dirs, run_batch, compute_metrics, MANIFEST_DIR, RESULTS

bootstrap_dirs()
rows = [
    r for r in read_csv(MANIFEST_DIR / 'final_manifest.csv')
    if r['case_id'] in {
        'forge_x_warn_001','forge_x_warn_010','forge_x_warn_015',
        'forge_x_reject_001','forge_x_reject_002','forge_x_reject_004',
        'forge_x_sanctions_tbml_shell_001','forge_x_sanctions_tbml_shell_002',
        'forge_x_ocr_noise_001','forge_x_ocr_noise_008',
    }
]
print('rows', len(rows))

results = run_batch(
    rows,
    api_url='http://localhost:8000/api/validate/',
    api_token='',
    dry_run=False,
    limit=None,
    resume_safe=False,
    max_retries_429=8,
    base_backoff_seconds=2.5,
    max_backoff_seconds=60.0,
    min_interval_seconds=0.9,
)
summary = compute_metrics(results)
print('summary', summary)

results_path = RESULTS / 'day3_results.jsonl'
metrics_path = RESULTS / 'metrics_summary.json'

dest_base = RESULTS / 'phase4_targeted_sample_'
for src in [results_path, metrics_path, RESULTS / 'failed_cases.csv', RESULTS / 'confusion_matrix.csv', RESULTS / 'DAY3_SIGNOFF.md', RESULTS / 'rate_limit_stats.json', RESULTS / 'validation_commands.ps1']:
    if src.exists():
        dst = Path(str(dest_base) + src.name)
        shutil.copy2(src, dst)
        print('saved', dst)
