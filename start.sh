#!/bin/bash

echo "============================================================"
echo "BRIDGING BRAIN v4 - AI-Powered Lender Matching"
echo "============================================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.10+ first"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install anthropic pandas openpyxl fastapi uvicorn python-multipart --quiet --break-system-packages 2>/dev/null || \
pip3 install anthropic pandas openpyxl fastapi uvicorn python-multipart --quiet

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo
    echo "WARNING: ANTHROPIC_API_KEY environment variable not set"
    echo "AI features will be disabled."
    echo
    echo "To enable AI, set your API key:"
    echo "  export ANTHROPIC_API_KEY=your-key-here"
    echo
fi

# Check for database
if [ ! -f "lenders.db" ]; then
    echo
    echo "Setting up database..."
    python3 setup_database.py Bridging_Lenders_Questionnaire_Responses_1.xlsx
fi

echo
echo "Starting server..."
echo "Open http://127.0.0.1:8000 in your browser"
echo "Press Ctrl+C to stop"
echo

python3 main.py
