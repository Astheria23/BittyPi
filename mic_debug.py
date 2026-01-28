import pyaudio
import numpy as np
import time
import wave
import sys

# Mock logic if ears cannot be imported comfortably or to keep it standalone
# But importing Ears ensures we test the ACTUAL logic being used.
from ears import Ears

def draw_bar(val, max_val=10000, width=50):
    percent = min(val / max_val, 1.0)
    bar_len = int(percent * width)
    return "#" * bar_len + "-" * (width - bar_len)

def main():
    print("🎤 Initializing Bitty Mic Debugger...")
    
    # Use the existing logic from ears.py to ensure we use the same device/settings
    try:
        ears = Ears()
    except Exception as e:
        print(f"Failed to init Ears: {e}")
        return
    
    info = ears.audio.get_device_info_by_index(ears.device_index)
    print(f"\n[INFO] Device Name: {info['name']}")
    print(f"[INFO] Sample Rate: {ears.rate} Hz")
    print(f"[INFO] Chunk Size: {ears.chunk}")
    print("\n📊 Real-time Mic Level (Press Ctrl+C to stop testing and save recording)")
    print("---------------------------------------------------------------")
    
    frames = []
    
    try:
        if ears.stream is None:
            ears._start_stream()
            
        while True:
            # Match the read logic from ears.py
            read_size = int(ears.chunk * (ears.rate / 16000))
            try:
                data = ears.stream.read(read_size, exception_on_overflow=False)
                frames.append(data)
                
                audio_data = np.frombuffer(data, dtype=np.int16)
                # Calculate RMS Volume
                if len(audio_data) > 0:
                    volume = np.sqrt(np.mean(audio_data.astype(np.float32)**2))
                else:
                    volume = 0
                
                # Print bar
                sys.stdout.write(f"\rVolume: {int(volume):05d} [{draw_bar(volume)}] ")
                sys.stdout.flush()
                
            except Exception as e:
                print(f"\nError reading stream: {e}")
                break
                
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
    finally:
        ears.close()

    if frames:
        print("\n💾 Saving 'debug_mic.wav'...")
        wf = wave.open("debug_mic.wav", 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
        wf.setframerate(ears.rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        print("✅ Saved! Transfer this file to your computer to listen to it.")
        print("   (Or use 'aplay debug_mic.wav' if you have speakers on the Pi)")

if __name__ == "__main__":
    main()
