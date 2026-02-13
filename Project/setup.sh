#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env from example if not exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Creating .env from example..."
        cp .env.example .env
        echo "Please edit .env to set your MODEL_PATH."
    else
        echo "Warning: .env.example not found."
    fi
fi

echo ""
echo "Setup complete!"
echo "IMPORTANT: Ensure you have downloaded the model and set MODEL_PATH in .env"
echo "To activate the environment, run: source venv/bin/activate"
