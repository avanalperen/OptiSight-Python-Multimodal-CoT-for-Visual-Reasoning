@echo off
echo ==========================================
echo OptiSight Windows Setup
echo ==========================================

echo Creating Python virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo Error: Failed to create virtual environment. Make sure Python is installed and in PATH.
    pause
    exit /b
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing PyTorch with CUDA support (Stable)...
echo This may take a while...
:: Installing PyTorch explicitly first to ensure CUDA version is correct (adjust cu118/cu121/cu124 based on your driver if needed, defaulting to stable)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

echo Installing other dependencies...
pip install -r requirements.txt

if not exist .env (
    if exist .env.example (
        echo Creating .env from example...
        copy .env.example .env
        echo Please edit .env to set your MODEL_PATH.
    )
)

echo.
echo ==========================================
echo Setup Complete!
echo IMPORTANT: 
echo 1. Download the Qwen2-VL model.
echo 2. Edit .env and set MODEL_PATH to the model folder.
echo 3. Run run.bat to start the server.
echo ==========================================
pause
