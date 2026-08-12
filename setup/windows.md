# Windows Setup Guide

These instructions are for setting up the OptiSight Dashboard on Windows.

> [!IMPORTANT]
> **GPU Requirement:** The Vision Language Models (VLMs) and Segmentation models require an NVIDIA GPU with CUDA support for acceptable performance. Running on CPU is possible but will be extremely slow.

## Step 1: Open PowerShell
Open PowerShell or Command Prompt in the project directory.

## Step 2: Create a Virtual Environment
It is recommended to use a Python virtual environment to avoid dependency conflicts.

```powershell
python -m venv venv
```

## Step 3: Activate the Virtual Environment
Activate the environment so that packages are installed locally in the project.

```powershell
.\venv\Scripts\Activate.ps1
```
*(Note: If you get an Execution Policy error, run `Set-ExecutionPolicy Unrestricted -Scope CurrentUser` and try again).*

## Step 4: Install Dependencies
Install all required Python packages from the `requirements.txt` file.

```powershell
pip install -r requirements.txt
```

## Step 5: Start the Server
Once everything is downloaded and installed (including maps and models mentioned in the main README), you can start the dashboard.

```powershell
python start.py
```
