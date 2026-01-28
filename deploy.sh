#!/bin/bash

git pull origin main

echo "📦 Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y libffi-dev libportaudio2 portaudio19-dev python3-dev libopenblas-dev

pip install -r requirements.txt
# Manual install for openwakeword to avoid onnxruntime dependency on Pi
pip install openwakeword==0.6.0 --no-deps
# Install tflite-runtime from Coral repo (reliable for Pi)
pip install tflite-runtime --extra-index-url https://google-coral.github.io/py-repo/
pm2 restart bitty-guard

echo "✅ Update selesai! Bitty Guard sudah running versi terbaru."
