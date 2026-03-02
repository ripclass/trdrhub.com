# Run this in an elevated PowerShell (Run as Administrator)
$ErrorActionPreference = 'Continue'

Write-Host '=== 1) Stop Docker + WSL ===' -ForegroundColor Cyan
Get-Process 'Docker Desktop','com.docker.backend','com.docker.proxy','com.docker.build','com.docker.vpnkit' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
wsl --shutdown

Write-Host '=== 2) Stop Docker service ===' -ForegroundColor Cyan
sc.exe stop com.docker.service

Write-Host '=== 3) Unregister Docker WSL distros (destructive for Docker images/containers/volumes cache) ===' -ForegroundColor Yellow
wsl --unregister docker-desktop
wsl --unregister docker-desktop-data

Write-Host '=== 4) Remove Docker local data folders ===' -ForegroundColor Yellow
$paths = @(
  "$env:LOCALAPPDATA\Docker",
  "$env:APPDATA\Docker",
  "$env:APPDATA\Docker Desktop",
  "$env:LOCALAPPDATA\Docker Desktop"
)
foreach ($p in $paths) {
  if (Test-Path $p) {
    Write-Host "Removing $p"
    Remove-Item -Recurse -Force $p -ErrorAction SilentlyContinue
  }
}

Write-Host '=== 5) Optional disk scan (non-destructive) ===' -ForegroundColor Cyan
chkdsk C: /scan

Write-Host '=== 6) Start Docker service + app ===' -ForegroundColor Cyan
sc.exe start com.docker.service
Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe'

Write-Host '=== 7) Wait for engine and verify ===' -ForegroundColor Cyan
$deadline=(Get-Date).AddMinutes(5)
$ok=$false
while((Get-Date)-lt $deadline){
  Start-Sleep -Seconds 8
  docker version *> $null
  if($LASTEXITCODE -eq 0){ $ok=$true; break }
}
if(-not $ok){
  Write-Host 'Docker engine did not become ready.' -ForegroundColor Red
  exit 1
}

docker version
wsl -l -v

Write-Host '=== 8) Recreate TRDRHub stack ===' -ForegroundColor Cyan
Set-Location 'H:\.openclaw\workspace\trdrhub.com'
docker compose build --no-cache api
docker compose up -d

Write-Host '=== 9) Phase-1 gates ===' -ForegroundColor Cyan
docker compose ps
Test-NetConnection localhost -Port 5432 | Select-Object ComputerName,RemotePort,TcpTestSucceeded
Test-NetConnection localhost -Port 6379 | Select-Object ComputerName,RemotePort,TcpTestSucceeded
Test-NetConnection localhost -Port 8000 | Select-Object ComputerName,RemotePort,TcpTestSucceeded
try { (Invoke-WebRequest -Uri 'http://localhost:8000/healthz' -UseBasicParsing -TimeoutSec 15).StatusCode } catch { $_.Exception.Message }
try { (Invoke-WebRequest -Uri 'http://localhost:8000/health/live' -UseBasicParsing -TimeoutSec 15).StatusCode } catch { $_.Exception.Message }

Write-Host '=== Done ===' -ForegroundColor Green
