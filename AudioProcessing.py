import sounddevice as sd
import numpy as np
import threading
import time
import queue
from typing import Optional, Callable

class AudioProcessor:
    def __init__(self, device_id: int, samplerate: int = 44100, buffer_size: int = 1024):
        self.device_id = device_id
        self.samplerate = samplerate
        self.buffer_size = buffer_size
        self.current_db = -120
        self.data_history = []
        self.timestamps = []
        self.stream = None
        self.data_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.data_lock = threading.Lock()
        self.max_history = 1000
        print(f"Using device: {sd.query_devices(device_id)['name']}")

    def __del__(self):
        self.close()

    def _callback(self, indata, frames, time_info, status):
        rms = np.sqrt(np.mean(indata**2))
        self.current_db = 20 * np.log10(max(rms, 1e-10) + 1e-6) + 100
        timestamp = time.time()
        
        with self.data_lock:
            self.data_history.append(self.current_db)
            self.timestamps.append(timestamp)
            if len(self.data_history) > self.max_history:
                self.data_history.pop(0)
                self.timestamps.pop(0)
        
        self.data_queue.put((timestamp, self.current_db))

    def create_stream(self):
        """Create a fresh stream instance"""
        if self.stream:
            self.stream.close()
        self.stream = sd.InputStream(
            device=self.device_id,
            samplerate=self.samplerate,
            blocksize=self.buffer_size,
            callback=self._callback,
            channels=1
        )

    def capture_audio(self, callback):
        """Main capture loop with proper stream management"""
        self.stop_event.clear()
        self.create_stream()
        
        try:
            with self.stream:
                while not self.stop_event.is_set():
                    while not self.data_queue.empty():
                        timestamp, db_level = self.data_queue.get()
                        callback(db_level)
                    time.sleep(0.1)
        except Exception as e:
            print(f"Audio capture error: {str(e)}")

    def start(self):
        """Start audio capture with a fresh stream"""
        self.stop_event.clear()
        self.create_stream()
        try:
            self.stream.start()
        except Exception as e:
            print(f"Error starting stream: {str(e)}")
            raise

    def stop(self):
        """Stop audio capture"""
        self.stop_event.set()

    def close(self):
        """Full cleanup"""
        self.stop_event.set()
        if self.stream:
            self.stream.close()
            self.stream = None