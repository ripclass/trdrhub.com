$ErrorActionPreference = "Stop"

# Safe smoke run preset: 20 cases, paced, resume-safe
python .\tools\day3_pipeline\run_batch_day3.py --smoke20 --min-interval 1.5 --retries-429 6

Write-Host "Expected smoke criteria: success_rate>=90%, HTTP429<=5%, PASS blocked<=20%"
Write-Host "See: data/day3/results/rate_limit_stats.json and data/day3/results/metrics_summary.json"
