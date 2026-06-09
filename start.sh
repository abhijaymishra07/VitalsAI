#!/bin/bash
# VitalsAI — run Streamlit app locally

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT" || exit 1

if [ ! -d backend/.venv ]; then
  echo "Creating virtualenv..."
  python3 -m venv backend/.venv
fi

source backend/.venv/bin/activate
pip install -q -r requirements.txt

if ! command -v tesseract >/dev/null 2>&1; then
  echo "WARNING: tesseract not installed — scanned PDFs/images won't OCR."
  echo "  Fix: sudo apt install tesseract-ocr tesseract-ocr-eng"
  echo ""
fi

echo "Starting VitalsAI at http://localhost:8501"
streamlit run streamlit_app.py --server.port 8501
