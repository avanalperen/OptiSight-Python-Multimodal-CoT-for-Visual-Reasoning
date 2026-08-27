# Windows Setup Guide (via WSL2)

Because **AI Habitat** is natively built for Linux and does not support native Windows, the only proper and headache-free way to run this project on Windows is by using **Windows Subsystem for Linux (WSL2)**. 

WSL2 allows you to run a full Linux environment inside Windows while seamlessly sharing your NVIDIA GPU for the VLM and Vision Foundation models.

> [!WARNING]
> **Storage Space Alert:** Setting up this project on Windows requires installing a full Linux virtual machine via WSL2 and creating Conda environments with heavy machine learning libraries. This setup will consume a **massive amount of disk space** (easily 30GB - 50GB+). If you have limited storage on your Windows drive, we highly recommend using a native Linux system instead.

> [!IMPORTANT]
> **Hardware Requirements:** Running AI Habitat along with large Vision Language Models (VLM) simultaneously will consume a significant amount of memory. We highly recommend at least **12GB+ GPU VRAM** and **16GB+ System RAM**. Make sure you have the official NVIDIA drivers installed on Windows (WSL2 will automatically use them).

## Step 1: Install WSL2 (Ubuntu)
Open **PowerShell as Administrator** in Windows and run:
```powershell
wsl --install
```
*Restart your computer if prompted. After restarting, a Linux terminal will open and ask you to create a UNIX username and password.*

## Step 2: Install Miniconda in WSL2
Open your **Ubuntu (WSL)** terminal and run the following commands to install Miniconda:
```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b
source ~/miniconda3/bin/activate
conda init
```
*Close the Ubuntu terminal and open a new one to apply the conda changes.*

## Step 3: Clone the Repository
In your **Ubuntu (WSL)** terminal:
```bash
git clone <YOUR_REPOSITORY_URL>
cd Project
```

## Step 4: Create and Activate the Conda Environment
We will create an environment named `habitat` (as is standard for AI Habitat projects):
```bash
conda create -n habitat python=3.10 -y
conda activate habitat
```

## Step 5: Install PyTorch (with CUDA)
Install PyTorch configured for your GPU to ensure the VLM and Segmentation models can be loaded into VRAM:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## Step 6: Install AI Habitat
Install AI Habitat directly from conda to avoid any C++ compilation headaches:
```bash
conda install habitat-sim -c aihabitat -c conda-forge -y
```

## Step 7: Install Remaining Dependencies
Install the rest of the project's dependencies:
```bash
pip install -r requirements.txt
```

## Step 8: Setup Models and Maps
As described in the main `README.md`:
1. Place your 3D Map archives (`.tar`) into the `habitats/` folder.
2. Download and place the required Model weights into the `models/` folder.

## Step 9: Start the Server
Once everything is set up, you can start the dashboard. The system will load the VLM into memory and initialize Habitat.
```bash
python start.py
```
*You can now open your normal Windows web browser and navigate to `http://localhost:8000`. WSL2 automatically forwards the ports to Windows!*
