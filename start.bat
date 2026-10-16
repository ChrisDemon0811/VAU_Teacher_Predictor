@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

if not defined VAU_PORT set "VAU_PORT=8000"

echo.
echo  VAU Teacher Predictor
echo  Mo trinh duyet tai: http://127.0.0.1:%VAU_PORT%
echo  Nhan Ctrl+C de dung server.
echo.

"%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port %VAU_PORT%

if errorlevel 1 (
    echo.
    echo Khong the khoi dong. Hay kiem tra Python va chay: pip install -r requirements.txt
    pause
)

endlocal
