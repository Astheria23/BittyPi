import openwakeword.utils
import os

print("Downloading hey_jarvis_v0.1.tflite...")
# This function downloads to the current directory by default
openwakeword.utils.download_models(model_names=["hey_jarvis_v0.1.tflite"])

if os.path.exists("hey_jarvis_v0.1.tflite"):
    print("Download successful!")
    # Move to models folder
    os.makedirs("models", exist_ok=True)
    os.rename("hey_jarvis_v0.1.tflite", "models/hey_jarvis_v0.1.tflite")
else:
    print("Download failed.")
