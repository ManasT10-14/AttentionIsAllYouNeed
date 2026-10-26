# Run from a normal PowerShell terminal to restart the local Odin stack.
[CmdletBinding()]
param([switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$taskLogs = Join-Path $taskRoot 'data\local-logs'
New-Item -ItemType Directory -Path $taskLogs -Force | Out-Null

& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    $dockerApp = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
    if (-not (Test-Path -LiteralPath $dockerApp)) { throw 'Docker Desktop is not installed.' }
    Start-Process -FilePath $dockerApp -WindowStyle Hidden
    $dockerReady = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Seconds 2
        & docker info *> $null
        if ($LASTEXITCODE -eq 0) { $dockerReady = $true; break }
    }
    if (-not $dockerReady) { throw 'Docker is unavailable. Open Docker Desktop and check engine permissions, then rerun this script.' }
}

# Stop only this project's database, preserving its volume.
& docker compose stop db
if ($LASTEXITCODE -ne 0) { throw 'Could not stop the project database.' }
$taskPorts = @(3000, 3001, 8000, 8110)
$taskOwners = Get-NetTCPConnection -State Listen -ErrorAction Stop |
    Where-Object { $_.LocalPort -in $taskPorts } |
    Select-Object -ExpandProperty OwningProcess -Unique
foreach ($taskOwner in $taskOwners) {
    if ($taskOwner -gt 0 -and $taskOwner -ne $PID) {
        Write-Host "Stopping process $taskOwner on an Odin application port."
        Stop-Process -Id $taskOwner -Force -ErrorAction Stop
    }
}
& docker compose up -d --wait db
if ($LASTEXITCODE -ne 0) { throw 'Database startup failed. Check docker compose logs db.' }

$env:PYTHONPATH = Join-Path $taskRoot 'backend'
$pythonExe = Join-Path $taskRoot '.venv\Scripts\python.exe'
$backendProcess = Start-Process -FilePath $pythonExe -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru `
    -ArgumentList @('-m', 'uvicorn', 'odin.api.main:app', '--host', '127.0.0.1', '--port', '8000') `
    -RedirectStandardOutput (Join-Path $taskLogs 'backend.out.log') -RedirectStandardError (Join-Path $taskLogs 'backend.err.log')
$backendReady = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    if ($backendProcess.HasExited) { break }
    try {
        $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2
        if ($health.ok) { $backendReady = $true; break }
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $backendReady) { throw "Backend startup failed. Read $taskLogs\backend.err.log" }

$frontendDir = Join-Path $taskRoot 'frontend'
$nextEntry = Join-Path $frontendDir 'node_modules\next\dist\bin\next'
$env:ODIN_LOCAL_SERVER = '1'
$env:ODIN_BUILD_DIR = '.next-pack-final'
$env:NEXT_PUBLIC_API_BASE_URL = '/'
$env:API_PROXY_TARGET = 'http://127.0.0.1:8000'
if (-not $SkipBuild -or -not (Test-Path -LiteralPath (Join-Path $frontendDir '.next-pack-final\BUILD_ID'))) {
    Push-Location -LiteralPath $frontendDir
    try {
        & node $nextEntry build --webpack
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
}
$frontendProcess = Start-Process -FilePath (Get-Command node).Source -WorkingDirectory $frontendDir -WindowStyle Hidden -PassThru `
    -ArgumentList @(('"' + $nextEntry + '"'), 'start', '--hostname', '127.0.0.1', '--port', '3000') `
    -RedirectStandardOutput (Join-Path $taskLogs 'frontend.out.log') -RedirectStandardError (Join-Path $taskLogs 'frontend.err.log')
$frontendReady = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    if ($frontendProcess.HasExited) { break }
    try {
        $page = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:3000/api/health' -TimeoutSec 2
        if ($page.StatusCode -eq 200) { $frontendReady = $true; break }
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $frontendReady) { throw "Frontend/proxy startup failed. Read $taskLogs\frontend.err.log" }
Write-Host 'Odin is ready at http://127.0.0.1:3000 (database and API health verified).'
