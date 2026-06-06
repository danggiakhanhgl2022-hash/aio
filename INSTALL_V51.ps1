# INSTALL_V51.ps1
$ErrorActionPreference = "Stop"

Write-Host "Dang dung Python/Streamlit cu..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

$Target = "D:\aio"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

if (!(Test-Path $Target)) {
    New-Item -ItemType Directory -Path $Target | Out-Null
}

Write-Host "Xoa src/runtime cu..." -ForegroundColor Yellow
Remove-Item -Recurse -Force "$Target\src" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$Target\runtime" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$Target\__pycache__" -ErrorAction SilentlyContinue

Write-Host "Copy code V51..." -ForegroundColor Yellow
Copy-Item "$Here\app.py" "$Target\app.py" -Force
Copy-Item "$Here\src" "$Target\src" -Recurse -Force
Copy-Item "$Here\requirements.txt" "$Target\requirements.txt" -Force

Set-Location $Target
Write-Host "Cai thu vien neu thieu..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host "Kiem tra version:" -ForegroundColor Yellow
python -c "from src.config import APP_VERSION; print(APP_VERSION)"

Write-Host ""
Write-Host "Xong. Chay app bang lenh:" -ForegroundColor Green
Write-Host "cd D:\aio"
Write-Host "python -m streamlit run app.py"
