@echo off
echo Starting Cafe24 Automation Hub (Development Mode)
echo Server will be available at: http://localhost:3000
echo.
cd /d "%~dp0"
python -m uvicorn web.app:app --reload --port 3000
pause