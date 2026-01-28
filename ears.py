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
TARGET_RATE = 16000
CHUNK = 1280
MIC_INDEX = None
SOFTWARE_GAIN = 4.0 # Boost volume digitaly

import scipy.signal

import scipy.signal

class Ears:
    def __init__(self, wake_word_threshold=0.5):
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.chunk = CHUNK
        self.rate = TARGET_RATE

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
        
        while not stop_event.is_set():
            # Read enough frames to get roughly CHUNK at TARGET_RATE
            # If rate is 48000, we need 3x the data to get same time duration
            read_size = int(self.chunk * (self.rate / TARGET_RATE))
            try:
                data = self.stream.read(read_size, exception_on_overflow=False)
            except OSError as e:
                print(f"[Ears] Read Error: {e}")
                continue

            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # Resample if needed
            # Resample if needed
            if self.rate != TARGET_RATE:
                # Number of samples we want
                target_samples = int(len(audio_data) * TARGET_RATE / self.rate)
                audio_data = scipy.signal.resample(audio_data, target_samples).astype(np.int16)

            # Apply Gain
            audio_data = (audio_data * SOFTWARE_GAIN).clip(-32768, 32767).astype(np.int16)

            # Feed to openWakeWord
            prediction = self.model.predict(audio_data)
            
            # Check prediction
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
            read_size = int(self.chunk * (self.rate / TARGET_RATE))
            try:
                data = self.stream.read(read_size, exception_on_overflow=False)
            except OSError:
                continue
                
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # Resample for VAD and saving
            if self.rate != TARGET_RATE:
                target_samples = int(len(audio_data) * TARGET_RATE / self.rate)
                audio_data = scipy.signal.resample(audio_data, target_samples).astype(np.int16)
                
            # Apply Gain
            audio_data = (audio_data * SOFTWARE_GAIN).clip(-32768, 32767).astype(np.int16)

            frames.append(audio_data.tobytes())
            
            # Simple VAD (Energy based)
            # Fix: Cast to float to avoid overflow during squaring
            energy = np.sqrt(np.mean(audio_data.astype(np.float64)**2))
            
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
        wf.setframerate(TARGET_RATE) # Always save as 16k
        wf.writeframes(b''.join(frames))
        wf.close()
        
        return os.path.abspath(filename)

    def _start_stream(self):
        if self.stream is not None:
            self.stream.close()
            
        supported_rates = [16000, 48000, 44100, 8000]
        
        for r in supported_rates:
            try:
                print(f"[Ears] Trying sample rate: {r}Hz...")
                self.stream = self.audio.open(
                    format=FORMAT,
                    channels=CHANNELS,
                    rate=r,
                    input=True,
                    input_device_index=self.device_index,
                    frames_per_buffer=int(CHUNK * (r / TARGET_RATE))
                )
                self.rate = r
                print(f"[Ears] Success! Running at {r}Hz")
                return
            except Exception as e:
                print(f"[Ears] Failed rate {r}: {e}")
                
        raise Exception("No supported sample rate found for this microphone")

    def close(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()
