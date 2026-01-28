import pyaudio
import numpy as np
import sys
import types

# Hack: openwakeword imports onnxruntime at top level.
# We want to use tflite-runtime on Pi, but the import crashes.
# We mock onnxruntime so the import passes, then usage uses tflite.
try:
    import onnxruntime
except ImportError:
    m = types.ModuleType("onnxruntime")
    sys.modules["onnxruntime"] = m

from openwakeword.model import Model
import collections
import time
import os
import wave
from typing import Tuple, Optional

# Constants
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280
MIC_INDEX = None  # Auto-detect or set manually if needed

class Ears:
    def __init__(self, wake_word_threshold=0.5):
        self.audio = pyaudio.PyAudio()
        self.stream = None

        self.threshold = wake_word_threshold
        
        # Determine mic index (prefer USB or I2S generic names if visible, else default)
        self.device_index = self._find_input_device()
        print(f"[Ears] Using Input Device Index: {self.device_index}")
        
        # Load local TFLite model
        self.model = Model(wakeword_models=["./models/hey_jarvis_v0.1.tflite"], inference_framework="tflite")

    def _find_input_device(self):
        count = self.audio.get_device_count()
        for i in range(count):
            info = self.audio.get_device_info_by_index(i)
            name = info.get('name').lower()
            # Common names for I2S/USB mics on Pi
            if 'dmic' in name or 'usb' in name or 'i2s' in name or 'voicehat' in name or 'google' in name:
                return i
        return None # Use default

    def listen_for_wake_word(self, stop_event) -> bool:
        """
        Listens continuously until wake word is detected or stop_event is set.
        Returns True if wake word detected, False otherwise.
        """
        if self.stream is None:
            self._start_stream()

        print("[Ears] Listening for 'Hey Jarvis'...")
        
        # Ring buffer to keep slight history (optional, handled by OWW mostly)
        while not stop_event.is_set():
            data = self.stream.read(CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # Feed to openWakeWord
            prediction = self.model.predict(audio_data)
            
            # Check prediction (returns dict like {'hey_jarvis': 0.002, ...})
            for mdl_name, score in prediction.items():
                if score > self.threshold:
                    print(f"[Ears] Wake Word Detected! ({score:.2f})")
                    return True
        
        return False

    def record_command(self, duration=5, silence_threshold=500, silence_duration=1.5) -> Optional[str]:
        """
        Records audio after wake word until silence or max duration.
        Saves to a temporary wav file and returns the path.
        """
        if self.stream is None:
            self._start_stream()
            
        print("[Ears] Recording command...")
        frames = []
        start_time = time.time()
        silence_start = None
        
        while (time.time() - start_time) < duration:
            data = self.stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            
            # Simple VAD (Energy based)
            audio_data = np.frombuffer(data, dtype=np.int16)
            energy = np.sqrt(np.mean(audio_data**2))
            
            if energy < silence_threshold:
                if silence_start is None:
                    silence_start = time.time()
                elif (time.time() - silence_start) > silence_duration:
                    print("[Ears] Silence detected, stopping recording.")
                    break
            else:
                silence_start = None
                
        # Save to file
        filename = "command.wav"
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        return os.path.abspath(filename)

    def _start_stream(self):
        if self.stream is not None:
            self.stream.close()
            
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=CHUNK
        )

    def close(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()
