# Linux Setup Guide

These instructions are the recommended way to set up the OptiSight Dashboard on Linux (Ubuntu/Debian, etc.) from scratch.

> [!IMPORTANT]
> **Hardware Requirements:** Running AI Habitat along with large Vision Language Models (VLM) simultaneously will consume a significant amount of memory. We highly recommend at least **12GB+ GPU VRAM** and **16GB+ System RAM**. Make sure you have the official NVIDIA drivers installed on your system.

## Prerequisites
1. **Git:** To clone the repository. (`sudo apt install git`)
2. **Miniconda / Anaconda:** Highly recommended for managing Python environments and installing AI Habitat without system conflicts. [Download Miniconda here](https://docs.anaconda.com/free/miniconda/index.html).

## Step 1: Clone the Repository
Open your terminal and clone the project:
```bash
git clone <YOUR_REPOSITORY_URL>
cd Project
```

## Step 2: Create and Activate the Conda Environment
We will create an environment named `habitat`:
```bash
conda create -n habitat python=3.10 -y
conda activate habitat
```

## Step 3: Install PyTorch (with CUDA)
Install PyTorch configured for your GPU to ensure the VLM and Segmentation models can be loaded into VRAM:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## Step 4: Install AI Habitat
AI Habitat must be installed via Conda to avoid complex C++ EGL/GLX compilation errors on Linux:
```bash
conda install habitat-sim -c aihabitat -c conda-forge -y
```

## Step 5: Install Remaining Dependencies
Install the rest of the required Python packages from the `requirements.txt` file:
```bash
pip install -r requirements.txt
```

## Step 6: Setup Models and Maps
As described in the main `README.md`:
1. Place your 3D Map archives (`.tar`) into the `habitats/` folder.
2. Download and place the required Model weights into the `models/` folder.

## Step 7: Start the Server
Once everything is set up, you can start the dashboard. The system will verify your resources, load the VLM into memory, and initialize Habitat.
```bash
python start.py
```
*Navigate to `http://localhost:8000` in your web browser.*
