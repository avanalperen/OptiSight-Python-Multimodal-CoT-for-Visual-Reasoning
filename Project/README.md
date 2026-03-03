# OptiSight Dashboard

## Requirements
- Ubuntu (WSL recommended for Windows users to use AI Habitat Sim)
- Python 3.8+
- CUDA GPU (NVIDIA Pascal+ recommended, e.g., GTX 1070)
- Habitat-Sim & Transformers

## Environment Setup
This project uses two Conda environments to maintain compatibility between AI Habitat (Python 3.9) and newer VLMs (Python 3.12).

### 1. Habitat Environment (Main)
Used for the dashboard and physics simulation.
```bash
cd "linux setup"
bash setup_conda.sh
conda activate habitat
```

### 2. Qwen 3.5 Bridge Environment (Automatic)
Used for high-performance Qwen 3.5-VL inference. The main server starts this automatically.
```bash
cd "linux setup"
bash setup_qwen35.sh
```

## Running the Application
1. Activate the main environment:
   ```bash
   conda activate habitat
   ```
2. Start the server:
   ```bash
   python server.py
   ```
3. Open your web browser and navigate to:
   http://localhost:8000
    
> **Note:** Qwen 3.5 models (0.8B/2B) are managed via a persistent bridge server for maximum speed and VRAM efficiency.

## Windows Users
- **Option 1 (Native)**: Photo/Video analysis only (No Sim). Run `windows setup/run_windows.bat`.
- **Option 2 (WSL - Recommended)**: Full features including AI Habitat. Follow the Linux setup steps inside a WSL Ubuntu terminal.

## Troubleshooting
- **CUDA Error (No Kernel Image)**: Ensure you are using the `qwen35` environment setup which includes CUDA 11.8 support for Pascal GPUs.
- **Memory Issues**: The system now uses resolution resizing (448px) and a bridge architecture to stay within 8GB VRAM limits.
