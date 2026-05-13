#!/bin/bash
# QML·PLACE Local Installation Script (Linux/macOS)

set -e

echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo " QML·PLACE Local Setup (Linux/macOS)"
echo "════════════════════════════════════════════════════════════════════════"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found. Please install Python 3.9+"
    exit 1
fi

echo "[OK] Python detected"
python3 --version

# Create virtual environment
echo ""
echo "[SETUP] Creating Python virtual environment..."
if [ -d "venv" ]; then
    echo "[WARN] Virtual environment already exists, skipping..."
else
    python3 -m venv venv
    echo "[OK] Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "[SETUP] Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "[SETUP] Upgrading pip..."
python -m pip install --upgrade pip --quiet || echo "[WARN] pip upgrade had issues, continuing..."

# Install dependencies
echo ""
echo "[SETUP] Installing Python dependencies (this may take 5-10 minutes)..."
echo "[INFO] Installing: PyQt6, PennyLane, PyTorch, NumPy, etc."
pip install -r requirements.txt

# Create directories
echo ""
echo "[SETUP] Creating directories..."
mkdir -p results checkpoints designs/CA234

echo "[OK] Directories created"

# Summary
echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo " SETUP COMPLETE ✓"
echo "════════════════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo ""
echo " 1. Prepare design files (if not already present):"
echo "    - Place CA234.v, CA234.sdc, CA234.def in designs/CA234/"
echo "    - Or use demo mode in GUI"
echo ""
echo " 2. Run the GUI application:"
echo "    python main.py"
echo ""
echo " 3. Or run tests:"
echo "    pytest -v"
echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo ""
