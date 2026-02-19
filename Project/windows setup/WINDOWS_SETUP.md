# Windows Setup Guide

This project can run on Windows in two modes:
1. **Native Windows (Partial)**: Supports Photo & Video analysis using Qwen2-VL. Does *not* support AI Habitat Simulation.
2. **WSL (Full)**: Supports all features including AI Habitat Simulation, running inside a Linux subsystem.

---

## Option 1: Native Windows (Easier, No Simulator)

### Prerequisites
1. **NVIDIA GPU Driver**: Installed on your Windows system.
2. **Miniconda or Anaconda**: [Download here](https://docs.anaconda.com/miniconda/).
3. **Microsoft Visual C++ Redistributable**: Likely already installed, but required for PyTorch.

### Installation Steps

1. **Open the Project Folder**:
   - Navigate to the `windows_setup` folder inside the project directory.

2. **Prepare the Model**:
   - Create a folder named `models` inside the project directory.
   - Place your `qwen2-vl-2b` model folder inside `models`.
   - Structure should look like:
     ```
     Project/
       models/
         qwen2-vl-2b/
           config.json
           ...
       windows_setup/
         run_windows.bat
       server.py
       ...
     ```
   - *Alternative*: If your model is elsewhere, edit `run_windows.bat` and set `MODEL_PATH`.

3. **Run the Setup Script**:
   - Double-click `run_windows.bat`.
   - This script will:
     - Check for Conda.
     - Create a new environment named `habitat-win` (this may take a few minutes the first time).
     - Install necessary libraries (`pytorch`, `transformers`, etc.).
     - Start the server.

4. **Access the Dashboard**:
   - The script should open your browser to `http://localhost:8000`.
   - If not, open it manually.

### Limitations
- **Sim Mode**: The "AI Habitat Sim" tab will show an error or be disabled because `habitat-sim` is not compatible with native Windows.
- **Paths**: Ensure your model path does not contain special characters if possible.

---

## Option 2: WSL (Full Features)

If you need the **AI Habitat Simulator**, you must use WSL (Windows Subsystem for Linux).

### Prerequisites
1. **Enable WSL**: Open PowerShell as Admin and run `wsl --install`. Restart if needed.
2. **Install Ubuntu**: Install Ubuntu 22.04 or 24.04 from the Microsoft Store.
3. **NVIDIA Drivers in WSL**: Windows 11 handles this automatically. Verify with `nvidia-smi` inside WSL.

### Installation Steps (Inside WSL)

1. Open your WSL terminal (Ubuntu).
2. Navigate to your project folder (e.g., `/mnt/c/Users/YourName/Desktop/...`).
3. Follow the **Linux/README.md** instructions:
   ```bash
   # Install Miniconda in WSL if not present
   mkdir -p ~/miniconda3
   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
   bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
   rm -rf ~/miniconda3/miniconda.sh
   source ~/miniconda3/bin/activate
   
   # Create Environment
   conda env create -f environment.yml
   
   # Activate and Run
   conda activate habitat
   python server.py
   ```

### Troubleshooting WSL
- If you get `libGL.so.1` errors: `sudo apt-get update && sudo apt-get install ffmpeg libsm6 libxext6 -y`.
