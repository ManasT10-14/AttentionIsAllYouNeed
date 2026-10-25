param([switch]$Live)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    uv sync --locked --all-extras
    if ($LASTEXITCODE -ne 0) { throw 'Dependency setup failed' }
    uv run --locked --all-extras ragnarok corpus-validate
    if ($LASTEXITCODE -ne 0) { throw 'Corpus validation failed' }
    uv run --locked --all-extras ragnarok corpus-build
    if ($LASTEXITCODE -ne 0) { throw 'Golden dataset compilation failed' }
    uv run --locked --all-extras pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Offline tests failed' }
    uv run --locked --all-extras ruff check src tests examples
    if ($LASTEXITCODE -ne 0) { throw 'Lint failed' }
    uv run --locked --all-extras ruff format --check src tests examples
    if ($LASTEXITCODE -ne 0) { throw 'Formatting check failed' }
    $resultCode = 0
    if ($Live) {
        if (-not (Test-Path -LiteralPath '.env')) { throw 'Live evaluation needs a local .env file' }
        foreach ($stage in @('retrieval', 'thor', 'rag', 'agent', 'security')) {
            Write-Host "Running live corpus stage: $stage"
            uv run --env-file .env --locked --all-extras ragnarok run --config "configs/corpus.$stage.json"
            $stageCode = $LASTEXITCODE
            if ($stageCode -eq 2) { $resultCode = 2 }
            elseif ($stageCode -eq 1 -and $resultCode -ne 2) { $resultCode = 1 }
            elseif ($stageCode -eq 3 -and $resultCode -eq 0) { $resultCode = 3 }
        }
        Write-Host 'Live quality results are in reports/corpus-*.json. A failed quality gate is preserved.'
    }
}
finally {
    Pop-Location
}
exit $resultCode
