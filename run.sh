#!/bin/bash
# Simple script to run the MCP server locally

# Check if .env file exists, create if not
if [ ! -f .env ]; then
    echo "Creating .env file..."
    echo "# Add your API keys below" > .env
    echo "GEMINI_API_KEY=" >> .env
    echo "YOUTUBE_API_KEY=" >> .env
    echo "Created .env file. Please edit it to add your API keys."
    exit 1
fi

# Check if Python virtual environment exists, create if not
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv .venv
    echo "Activating virtual environment and installing dependencies..."
    source .venv/bin/activate
    pip install -e .
else
    echo "Activating existing virtual environment..."
    source .venv/bin/activate
fi

# Run the server
echo "Running MCP server..."
python main.py 