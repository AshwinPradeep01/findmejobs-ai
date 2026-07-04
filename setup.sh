#!/bin/bash
set -e

echo ""
echo "  ============================================"
echo "   FindMeJobs.ai — One-Time Setup"
echo "  ============================================"
echo ""

# Check Python is available
if ! command -v python3 &> /dev/null; then
    echo "  [ERROR] python3 is not installed."
    echo "  Install it via: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

echo "  [1/4] Creating Python virtual environment..."
python3 -m venv .venv

echo "  [2/4] Activating virtual environment..."
source .venv/bin/activate

echo "  [3/4] Installing Python dependencies..."
pip install -r requirements.txt

echo "  [4/4] Installing Playwright Chromium browser..."
playwright install chromium

echo ""
echo "  ============================================"
echo "   Setup complete!"
echo "  ============================================"
echo ""
echo "  To start the app, run:  ./start.sh"
echo ""
