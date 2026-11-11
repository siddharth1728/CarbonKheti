# Launch CarbonKheti PS-13 Full-Stack Prototype
$ErrorActionPreference = "Stop"
Write-Host "Starting CarbonKheti PS-13 MRV Platform on http://127.0.0.1:8000 ..." -ForegroundColor Green
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

