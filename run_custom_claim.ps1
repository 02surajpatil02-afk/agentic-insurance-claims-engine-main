# Custom claim runner for Agentic Insurance Claims Engine
# Usage:
#   .\run_custom_claim.ps1
#   .\run_custom_claim.ps1 -ClaimFile sample_claims\over_threshold.txt
#   .\run_custom_claim.ps1 -List
#   .\run_custom_claim.ps1 -Resume CLM-XXXXXXXX -Action approve

param(
    [string]$ClaimFile = "sample_claims\custom_my_claim.txt",
    [switch]$List,
    [string]$Resume = "",
    [ValidateSet("approve", "reject", "")]
    [string]$Action = "",
    [string]$Notes = "Authorized following caseworker review."
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = if (Test-Path ".\.venv\Scripts\python.exe") {
    ".\.venv\Scripts\python.exe"
} else {
    "python"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Custom Claims Pipeline Runner" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($List) {
    Write-Host "`n[LIST] Persisted claims in state/ ..." -ForegroundColor Yellow
    & $Python cli.py --list
    exit $LASTEXITCODE
}

if ($Resume) {
    if (-not $Action) {
        Write-Host "Error: -Action approve|reject is required with -Resume" -ForegroundColor Red
        exit 1
    }
    Write-Host "`n[RESUME] Claim $Resume with action=$Action ..." -ForegroundColor Yellow
    & $Python cli.py --resume $Resume --action $Action --notes $Notes
    exit $LASTEXITCODE
}

if (-not (Test-Path $ClaimFile)) {
    Write-Host "Error: Claim file not found: $ClaimFile" -ForegroundColor Red
    exit 1
}

Write-Host "`n[1/1] Ingest + run pipeline on: $ClaimFile" -ForegroundColor Yellow
Write-Host "Backend stages: INGESTION -> EXTRACTION -> VALIDATION -> ROUTER -> LETTER/HITL" -ForegroundColor DarkGray
Write-Host ""

& $Python cli.py --sample $ClaimFile
$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "Tip: list all claims with:  .\run_custom_claim.ps1 -List" -ForegroundColor DarkGray
Write-Host "Tip: resume HITL claim:    .\run_custom_claim.ps1 -Resume CLM-XXXX -Action approve" -ForegroundColor DarkGray
exit $exitCode
