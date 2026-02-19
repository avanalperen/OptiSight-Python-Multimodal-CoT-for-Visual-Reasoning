# OptiSight Dashboard

## Requirements
- Ubuntu
- Python 3.8+
- CUDA GPU (Optional, for faster inference)
- Torchvision, Av

## 0. Prerequisites (Installing Conda)
If you do not have Conda installed, we recommend **Miniconda** (a lightweight version).

**Quick Install (Linux):**
```bash
mkdir -p ~/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm -rf ~/miniconda3/miniconda.sh
source ~/miniconda3/bin/activate
conda init --all
```
*After running these commands, close and reopen your terminal.*

## Setup (Conda)
1. Ensure you have Anaconda or Miniconda installed.
2. Open a terminal in this directory.
3. Run the setup script to create the environment:
   ```bash
   cd linux_setup
   bash setup_conda.sh
   cd ..
   ```
   Or manually:
   ```bash
   conda env create -f linux_setup/environment.yml
   ```

## Running the Application
1. Activate the Conda environment:
   ```bash
   conda activate habitat
   ```
2. Start the server:
   ```bash
   python server.py
   ```
3. Open your web browser and navigate to:
   http://localhost:8000
   
> **Note:** The model path is `/home/aavan/Desktop/Project Files/Vision Language Models/qwen2-vl-2b`.

## Deactivating the Environment
To exit the environment when you are done, simply run:
```bash
conda deactivate
```

## Troubleshooting
- If you see `Segmentation fault`, ensure `bitsandbytes` is not forcing 4-bit mode on unsupported GPUs. The server now defaults to `float16` or CPU fallback.
