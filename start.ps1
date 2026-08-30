Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  Starting DigitalTwin.ai Server" -ForegroundColor Green
Write-Host "  URL: http://localhost:8000" -ForegroundColor Yellow
Write-Host "===================================================" -ForegroundColor Cyan
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
