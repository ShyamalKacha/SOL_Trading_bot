@echo off
cd /d "%~dp0"

REM Check if venv exists, if not create it
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

REM Run the application
echo Starting the Solana Trading Bot application...
python -m app.main

REM Keep the window open
pause