#!/bin/bash

# Define environment name from the yml file
ENV_NAME=$(grep "name:" environment_qwen35.yml | head -n 1 | cut -d ' ' -f 2)

echo "Setting up Qwen 3.5 Bridge environment: $ENV_NAME"

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "Error: Conda is not installed or not in PATH."
    exit 1
fi

# Create environment from yml file
echo "Creating/Updating environment from environment_qwen35.yml..."
conda env create -f environment_qwen35.yml || conda env update -f environment_qwen35.yml --prune

echo "Setup for $ENV_NAME complete."
echo "Note: This environment is used automatically by server.py as a bridge server."
