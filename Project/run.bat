@echo off
if not exist venv (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b
)

echo Activating environment...
call venv\Scripts\activate

echo Starting server...
python server.py
pause
