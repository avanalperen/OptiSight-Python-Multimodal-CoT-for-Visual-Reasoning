@echo off
setlocal

:: Change to the directory of this batch file so it works from anywhere
cd /d "%~dp0"

:: Define environment names
set "ENV_NAME=habitat-win"
set "QWEN_ENV_NAME=qwen35"

:: Configuration (Optional)
:: Uncomment and set the following line if your model is in a custom location
:: set "MODEL_PATH=C:\path\to\your\model"
:: Otherwise, it defaults to: logic inside config.py

:: Check if Conda is available
where conda >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Conda is not found in your PATH.
    echo Please install Anaconda or Miniconda and fallback to the README instructions.
    pause
    exit /b 1
)

:: 1. Check and create Qwen 3.5 Bridge Environment
echo Checking for Qwen 3.5 bridge environment: %QWEN_ENV_NAME%...
call conda activate %QWEN_ENV_NAME%
if %ERRORLEVEL% NEQ 0 (
    echo Environment '%QWEN_ENV_NAME%' not found. Creating it now...
    call conda env create -f environment_qwen35_win.yml
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to create %QWEN_ENV_NAME% environment.
        pause
        exit /b 1
    )
) else (
    echo Environment '%QWEN_ENV_NAME%' already exists.
)

:: 2. Check and create Main Windows Environment
echo Checking for main environment: %ENV_NAME%...
call conda activate %ENV_NAME%
if %ERRORLEVEL% NEQ 0 (
    echo Environment '%ENV_NAME%' not found. Creating it now...
    call conda env create -f environment_windows.yml
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to create %ENV_NAME% environment.
        pause
        exit /b 1
    )
    call conda activate %ENV_NAME%
) else (
    echo Environment '%ENV_NAME%' is activated.
)

:: Run the server
echo Starting Server...
pushd ..
if defined MODEL_PATH (
    echo Model Path: %MODEL_PATH%
)
python server.py
popd

:: Pause on exit to see errors
pause
