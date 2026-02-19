#!/bin/bash

# Define environment name from the yml file (assumes 'name: habitat' is in the first few lines)
ENV_NAME=$(grep "name:" environment.yml | cut -d ' ' -f 2)

echo "Setting up Conda environment: $ENV_NAME"

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "Error: Conda is not installed or not in PATH."
    echo "---------------------------------------------------"
    echo "To install Miniconda (Recommended for Linux):"
    echo "1. Run: mkdir -p ~/miniconda3"
    echo "2. Run: wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh"
    echo "3. Run: bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3"
    echo "4. Run: source ~/miniconda3/bin/activate"
    echo "---------------------------------------------------"
    exit 1
fi

# Create environment from yml file
echo "Creating/Updating environment from environment.yml..."
conda env create -f environment.yml || conda env update -f environment.yml --prune

echo "Setup complete."
echo "To activate the environment, run:"
echo "conda activate $ENV_NAME"
