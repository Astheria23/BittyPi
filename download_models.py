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

print("Downloading hey_jarvis_v0.1.tflite...")
openwakeword.utils.download_models(model_names=["hey_jarvis_v0.1.tflite"])

# It likely downloaded to the openwakeword package directory
package_dir = os.path.dirname(openwakeword.__file__)
source_path = os.path.join(package_dir, "resources/models/hey_jarvis_v0.1.tflite")

target_path = "models/hey_jarvis_v0.1.tflite"

if os.path.exists(source_path):
    print(f"Found model at: {source_path}")
    os.makedirs("models", exist_ok=True)
    # Remove empty/corrupt file if exists
    if os.path.exists(target_path):
        os.remove(target_path)
    
    shutil.copy(source_path, target_path)
    print(f"✅ Success! Moved to {target_path}")
elif os.path.exists("hey_jarvis_v0.1.tflite"):
    # Fallback: Check CWD
    print("Found model in CWD")
    os.makedirs("models", exist_ok=True)
    if os.path.exists(target_path):
        os.remove(target_path)
    shutil.move("hey_jarvis_v0.1.tflite", target_path)
    print(f"✅ Success! Moved to {target_path}")
else:
    print(f"❌ Error: Model not found at {source_path} or CWD")
    # Debug info
    print(f"Package dir: {package_dir}")
    print(f"Contents of resources/models: {os.listdir(os.path.join(package_dir, 'resources/models'))}")
