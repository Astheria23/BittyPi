#!/bin/bash

echo "🚀 Memulai proses update Bitty Guard..."

git pull origin main
pip install -r requirements.txt
pm2 restart bitty-guard

echo "✅ Update selesai! Bitty Guard sudah running versi terbaru."
