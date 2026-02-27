Param(
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root

Write-Host "[Day3] Running local autopilot..." -ForegroundColor Cyan

$pyArgs = @(".\tools\day3_pipeline\run_day3_pipeline.py")
if ($DryRun) { $pyArgs += "--dry-run" }

python @pyArgs

Write-Host "[Day3] Done. Review outputs under data\day3\results" -ForegroundColor Green
