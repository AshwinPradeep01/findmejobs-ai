#!/bin/bash
set -e

echo ""
echo "  ============================================"
echo "   FindMeJobs.ai — Starting Server"
echo "  ============================================"
echo ""

# Check virtual environment exists
if [ ! -f ".venv/bin/activate" ]; then
    echo "  [ERROR] Virtual environment not found."
    echo "  Please run ./setup.sh first."
    exit 1
fi

echo "  Activating virtual environment..."
source .venv/bin/activate

echo "  Starting server on http://127.0.0.1:8000 ..."
echo ""
echo "  Press Ctrl+C to stop the server."
echo ""

# Open browser after a short delay (works on Linux/macOS)
( sleep 3 && (xdg-open http://127.0.0.1:8000 2>/dev/null || open http://127.0.0.1:8000 2>/dev/null || true) ) &

# Start the server (blocks until Ctrl+C)
python -m uvicorn app:app --host 127.0.0.1 --port 8000
