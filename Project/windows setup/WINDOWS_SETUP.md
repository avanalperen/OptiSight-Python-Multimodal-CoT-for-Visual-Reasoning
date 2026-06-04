# Windows Setup Guide

This project can run on Windows in two modes:
1. **Native Windows (Partial)**: Supports Photo & Video analysis using Vision-Language Models. Does *not* support AI Habitat Simulation.
2. **WSL (Full)**: Supports all features including AI Habitat Simulation, running inside a Linux subsystem.

---

## Option 1: Native Windows (Easier, No Simulator)

### Installation Steps

1. **Run the Setup Script**:
   - Navigate to the `windows setup` folder and double-click `run_windows.bat`.
   - This script will automatically create two Conda environments:
     - `qwen35`: A bridge environment used for high-performance model inference.
     - `habitat-win`: The main environment for the dashboard and UI.
   - Wait for both environments to be created and the server to start.

2. **Access the Dashboard**:
   - Once the server is running, open your browser and navigate to `http://localhost:8000`.

---

## Option 2: WSL (Full Features - RECOMMENDED)

If you need the **AI Habitat Simulator** and full system capabilities, you must use WSL (Windows Subsystem for Linux).

### Installation Steps (Inside WSL)

1. Open your WSL terminal (Ubuntu).
2. Navigate to your project folder.
3. Follow the **README.md** instructions to set up **both** environments:
   ```bash
   # 1. Dashboard & Sim Env
   bash "linux setup/setup_conda.sh"
   
   # 2. Qwen 3.5 Bridge Env (Crucial for Speed)
   bash "linux setup/setup_qwen35.sh"
   
   # 3. Run
   # Open the WSL terminal from Windows PowerShell
   wsl
   
   # Inside WSL, activate the environment and start the server
   conda activate habitat
   python server.py
   ```

### Troubleshooting WSL
- **CUDA Errors**: If you have a Pascal GPU (GTX 10 series) or older hardware, make sure you use the automated `setup_qwen35.sh` script which installs the correct CUDA 11.8 drivers.
- **Model Paths**: Check `config.py` to ensure `QWEN_PATH` and `SAM2_PATH` are either valid local paths or HuggingFace repo IDs.
