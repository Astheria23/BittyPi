#!/bin/bash

echo "🚀 Memulai proses update Bitty Guard..."

git pull origin main
pip install -r requirements.txt
# Manual install for openwakeword to avoid onnxruntime dependency on Pi
pip install openwakeword==0.6.0 --no-deps
# Install tflite-runtime from Coral repo (reliable for Pi)
pip install tflite-runtime --extra-index-url https://google-coral.github.io/py-repo/
pm2 restart bitty-guard

echo "✅ Update selesai! Bitty Guard sudah running versi terbaru."
