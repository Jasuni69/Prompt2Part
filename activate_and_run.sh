#!/bin/bash
# Convenience script to activate virtual environment and run the GUI

echo "🚀 Activating virtual environment..."
source venv/bin/activate

echo "📦 Virtual environment activated!"
echo "🎯 Starting Prompt2Part GUI..."
python3 gui/main.py 