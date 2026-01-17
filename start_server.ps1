# PowerShell script to start Flask server
Set-Location $PSScriptRoot

if (Test-Path "venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
}

Write-Host "Starting Flask server on http://127.0.0.1:5000" -ForegroundColor Green
python app.py


