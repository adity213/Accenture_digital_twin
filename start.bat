@echo off
title DigitalTwin.ai Local Server
echo ===================================================
echo   Starting DigitalTwin.ai Server
echo   URL: http://localhost:8000
echo ===================================================
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
pause
