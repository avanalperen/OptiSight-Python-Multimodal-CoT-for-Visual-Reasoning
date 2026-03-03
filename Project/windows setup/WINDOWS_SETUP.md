# Windows Setup Guide

This project can run on Windows in two modes:
1. **Native Windows (Partial)**: Supports Photo & Video analysis using Qwen2-VL. Does *not* support AI Habitat Simulation.
2. **WSL (Full)**: Supports all features including AI Habitat Simulation, running inside a Linux subsystem.

---

## Option 1: Native Windows (Easier, No Simulator)

### Installation Steps

1. **Run the Setup Script**:
   - Double-click `run_windows.bat` to create the `habitat-win` environment.
   - **Important for Qwen 3.5**: You must also create the bridge environment manually:
     ```bash
     conda env create -f "windows setup/environment_qwen35_win.yml"
     ```

2. **Access the Dashboard**:
   - Navigate to `http://localhost:8000`.

---

## Option 2: WSL (Full Features - RECOMMENDED)

If you need the **AI Habitat Simulator** and modern VLMs (Qwen 3.5), you must use WSL.

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
   conda activate habitat
   python server.py
   ```

### Troubleshooting WSL
- **CUDA Errors**: If you have a Pascal GPU (GTX 10 series), use the automated `setup_qwen35.sh` which installs the correct CUDA 11.8 drivers.
