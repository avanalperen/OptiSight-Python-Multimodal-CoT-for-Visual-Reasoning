# OptiSight - Python Multimodal CoT for Visual Reasoning

This project provides a web-based dashboard for performing visual reasoning tasks (analysis of images, videos, and habitat simulations) using the Qwen2-VL model.

## Features
- **Multimodal Analysis**: Upload photos or videos for analysis.
- **Real-time Video Stream Analysis**: Analyze video feeds frame-by-frame.
- **Custom Prompts**: Provide specific instructions for visual analysis.
- **Resource Monitoring**: Track RAM and GPU usage.
- **Result Saving**: Save analysis outputs for later review.

## Requirements
- Python 3.8+
- Nvidia GPU (recommended for performance, supports CUDA)
  - Successfully tested with **RTX 3060**.
- About 4-6GB VRAM for Qwen2-VL-2B (fp16).
- 8GB+ System RAM.

## Installation

1. **Clone or Download** this repository.
2. **Run Setup Script**:
   This script creates a virtual environment and installs dependencies.
   ```bash
   ./setup.sh
   ```
   Or manually:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Download Model**:
   You need to download the Qwen2-VL-2B-Instruct model (or similar).
   - Recommended source: [HuggingFace](https://huggingface.co/Qwen/Qwen2-VL-2B-Instruct)
   - Download the files and place them in a folder (e.g., `models/qwen2-vl-2b`).

4. **Configuration**:
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and set `MODEL_PATH` to the absolute path where you downloaded the model.
   ```
   MODEL_PATH=/path/to/your/models/qwen2-vl-2b
   ```

## Usage

1. **Activate Environment**:
   ```bash
   source venv/bin/activate
   ```

2. **Run Server**:
   ```bash
   python3 server.py
   ```
   The application should automatically open in your browser at `http://localhost:8000`.

## Windows Installation & Usage

1. **Install Python**: Ensure Python 3.8+ is installed and added to PATH.
2. **Run Setup**:
   Double-click `setup.bat`. This will create a virtual environment, install PyTorch with CUDA support (cu121), and other dependencies.
3. **Configuration**:
   Copy `.env.example` to `.env` (the script might do this for you) and edit it to point to your model path.
4. **Run Server**:
   Double-click `run.bat`.

### Note on bitsandbytes (Windows)
This project configuration excludes `bitsandbytes` by default to ensure compatibility on Windows. The server runs in FP16/FP32 mode, which works fine on GPUs like GTX 3060/RTX series without it. If you specifically need 4-bit/8-bit quantization:
- You may need to install a Windows-compatible version manually.

## Directory Structure
- `server.py`: Main backend application (FastAPI).
- `templates/`: HTML/JS frontend.
- `prompts/`: Saved custom prompts.
- `results/`: Saved analysis results.
- `test images/` & `test videos/`: Sample media.

## Troubleshooting
- **CUDA/GPU Issues**: Ensure you have installed the correct PyTorch version for your CUDA driver. The `requirements.txt` installs a standard version, but you may need to install a specific one from [pytorch.org](https://pytorch.org/).
