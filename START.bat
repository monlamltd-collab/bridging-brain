@echo off
echo ============================================================
echo BRIDGING BRAIN v4 - AI-Powered Lender Matching
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install anthropic pandas openpyxl fastapi uvicorn python-multipart --quiet

REM Check for API key
if "%ANTHROPIC_API_KEY%"=="" (
    echo.
    echo WARNING: ANTHROPIC_API_KEY environment variable not set
    echo AI features will be disabled.
    echo.
    echo To enable AI, set your API key:
    echo   set ANTHROPIC_API_KEY=your-key-here
    echo.
)

REM Check for database
if not exist lenders.db (
    echo.
    echo Setting up database...
    python setup_database.py Bridging_Lenders_Questionnaire_Responses_1.xlsx
)

echo.
echo Starting server...
echo Open http://127.0.0.1:8000 in your browser
echo Press Ctrl+C to stop
echo.

python main.py
