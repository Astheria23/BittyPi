import sys
import types
# Mock onnxruntime to bypass import error on Pi
try:
    import onnxruntime
except ImportError:
    m = types.ModuleType("onnxruntime")
    sys.modules["onnxruntime"] = m

import openwakeword.utils
import os

# Mock onnxruntime (already done above)
# ... imports ...
import openwakeword
import shutil
import os

# Mock onnxruntime (already done above)
# ... imports ...
import openwakeword
import shutil
import os
import requests

MODEL_URL = "https://github.com/dscripka/openWakeWord/blob/main/openwakeword/resources/models/hey_jarvis_v0.1.tflite?raw=true"
TARGET_PATH = "models/hey_jarvis_v0.1.tflite"

print(f"Downloading hey_jarvis_v0.1.tflite from {MODEL_URL}...")

os.makedirs("models", exist_ok=True)
if os.path.exists(TARGET_PATH):
    os.remove(TARGET_PATH)

try:
    response = requests.get(MODEL_URL, stream=True)
    response.raise_for_status()
    with open(TARGET_PATH, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    # Verify size
    if os.path.getsize(TARGET_PATH) < 1000:
        print("❌ Error: Downloaded file is too small (likely HTML).")
    else:
        print(f"✅ Success! Downloaded to {TARGET_PATH} ({os.path.getsize(TARGET_PATH)} bytes)")

except Exception as e:
    print(f"❌ Error downloading: {e}")
