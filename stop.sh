#!/bin/bash
pkill -f "streamlit run streamlit_app.py" 2>/dev/null || true
echo "Stopped VitalsAI Streamlit."
