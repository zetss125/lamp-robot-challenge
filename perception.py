import cv2
import json
import pyaudio
import requests
import base64
from vosk import Model, KaldiRecognizer

class PerceptionModule:
    def __init__(self, ollama_url="http://localhost:11434"):
        self.ollama_url = ollama_url
        
        # Initialize OpenCV Camera
        self.cap = cv2.VideoCapture(0)
        
        # Load Haar Cascade for fast, lightweight face detection (engagement)
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Initialize Vosk for lightweight offline STT
        # Note: Requires a downloaded vosk model in a folder named 'model' in the root directory
        try:
            self.vosk_model = Model("model")
            self.recognizer = KaldiRecognizer(self.vosk_model, 16000)
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
            self.stream.start_stream()
        except Exception as e:
            print("Failed to initialize Vosk (make sure you downloaded a model to the 'model' directory):", e)
            self.stream = None

    def check_engagement(self):
        """Returns True if a face is detected looking at the camera."""
        ret, frame = self.cap.read()
        if not ret:
            return False
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        # If we detect at least one face, consider it engagement
        return len(faces) > 0

    def listen(self):
        """Listens to microphone using Vosk and returns the transcribed text."""
        print("Listening...")
        if not self.stream:
            return ""
            
        while True:
            data = self.stream.read(4000, exception_on_overflow=False)
            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "")
                if text:
                    return text

    def analyze_scene(self):
        """Captures a frame and asks local Moondream2 what it sees via Ollama."""
        ret, frame = self.cap.read()
        if not ret:
            return []
            
        # Encode frame to base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        payload = {
            "model": "moondream2",
            "prompt": "List the main objects in this scene as a comma separated list.",
            "images": [frame_base64],
            "stream": False
        }
        
        try:
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            objects_str = data.get("response", "")
            return [obj.strip() for obj in objects_str.split(",") if obj.strip()]
        except Exception as e:
            print("Failed to query Moondream2 via Ollama:", e)
            return []

    def cleanup(self):
        self.cap.release()
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()
