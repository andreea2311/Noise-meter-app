from AudioProcessing import AudioProcessor
from Visualization import NoiseMeterApp
import sounddevice as sd

if __name__ == "__main__":
    print("Starting Real-Time Noise Meter...")
    processor = AudioProcessor(device_id=5)  
    
    app = NoiseMeterApp(processor)
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nApplication closed by user")
    finally:
        processor.close()