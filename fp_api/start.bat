@echo off
chcp 65001 >nul
echo Starting Invoice Box API Service...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found, please install Python 3.8+
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Start service
echo Starting API service...
echo.
echo Service will start at http://localhost:8000
echo API docs: http://localhost:8000/docs
echo Press Ctrl+C to stop service
echo.

python main_refactored.py

pause
