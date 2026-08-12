param(
    [int]$Port = 8000
)

$agentsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $agentsDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Project virtual environment was not found. Install the dependencies described in README first."
    exit 1
}

Set-Location -LiteralPath $agentsDir
& $python -m telco_local.web_app --port $Port
