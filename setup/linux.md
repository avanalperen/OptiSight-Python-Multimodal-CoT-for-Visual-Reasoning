# Linux Setup Guide

These instructions are for setting up the OptiSight Dashboard on Linux (Ubuntu/Debian, etc.).

> [!IMPORTANT]
> **GPU Requirement:** The Vision Language Models (VLMs) and Segmentation models require an NVIDIA GPU with CUDA support for acceptable performance. Running on CPU is possible but will be extremely slow. Make sure you have the official NVIDIA drivers installed.

## Step 1: Open Terminal
Navigate into the project directory using your terminal.

```bash
cd /path/to/project
```

## Step 2: Create a Virtual Environment
It is recommended to use a Python virtual environment to avoid dependency conflicts with system packages. If you don't have `venv` installed, run `sudo apt install python3-venv`.

```bash
python3 -m venv venv
```

## Step 3: Activate the Virtual Environment
Activate the environment so that packages are installed locally in the project.

```bash
source venv/bin/activate
```

## Step 4: Install Dependencies
Install all required Python packages from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

## Step 5: Start the Server
Once everything is downloaded and installed (including maps and models mentioned in the main README), you can start the dashboard.

```bash
python start.py
```
