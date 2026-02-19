@echo off
setlocal

:: Define environment name
set "ENV_NAME=habitat-win"

:: Configuration (Optional)
:: Uncomment and set the following line if your model is in a custom location
:: set "MODEL_PATH=C:\path\to\your\model"
:: Otherwise, it defaults to: logic inside config.py (usually models/qwen2-vl-2b relative to this folder)

:: Check if Conda is available
where conda >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Conda is not found in your PATH.
    echo Please install Anaconda or Miniconda and fallback to the README instructions.
    pause
    exit /b 1
)

:: Activate Conda environment
echo Activating environment: %ENV_NAME%...
call conda activate %ENV_NAME%
if %ERRORLEVEL% NEQ 0 (
    echo Environment '%ENV_NAME%' not found. Creating it now...
    conda env create -f environment_windows.yml
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to create environment.
        pause
        exit /b 1
    )
    call conda activate %ENV_NAME%
)

:: Run the server
echo Starting Server...
pushd ..
echo Model Path: %MODEL_PATH%
python server.py
popd

:: Pause on exit to see errors
pause
