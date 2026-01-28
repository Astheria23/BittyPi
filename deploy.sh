#!/bin/bash

echo "🚀 Memulai proses update Bitty Guard..."

git pull origin main
pip install -r requirements.txt
# Manual install for openwakeword to avoid onnxruntime dependency on Pi
pip install openwakeword==0.6.0 --no-deps
pm2 restart bitty-guard

echo "✅ Update selesai! Bitty Guard sudah running versi terbaru."
