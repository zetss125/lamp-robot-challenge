import base64
import json
import time
from typing import List, Optional

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import pyaudio
except ImportError:
    pyaudio = None

try:
    from vosk import KaldiRecognizer, Model
except ImportError:
    Model = None
    KaldiRecognizer = None

import requests


class PerceptionModule:
    """Handles laptop camera engagement, scene visual analysis, and microphone STT."""

    def __init__(self, ollama_url: str = "http://localhost:11434", vision_model: str = "moondream", timeout_s: float = 12.0):
        self.ollama_url = ollama_url
        self.vision_model = vision_model
        self.timeout_s = timeout_s
        self.force_engaged = False

        # Initialize OpenCV Camera
        self.cap = None
        self.face_cascade = None
        if cv2:
            try:
                self.cap = cv2.VideoCapture(0)
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
            except Exception as exc:
                print(f"Warning: OpenCV video capture initialization failed: {exc}")

        # Initialize Vosk for lightweight offline STT
        self.vosk_model = None
        self.recognizer = None
        self.audio = None
        self.stream = None
        if Model and KaldiRecognizer and pyaudio:
            try:
                self.vosk_model = Model("model")
                self.recognizer = KaldiRecognizer(self.vosk_model, 16000)
                self.audio = pyaudio.PyAudio()
                self.stream = self.audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
                self.stream.start_stream()
            except Exception as exc:
                print(f"Notice: Vosk STT initialization skipped (e.g. no local 'model' directory): {exc}")
                self.stream = None
                self.audio = None

    def check_engagement(self) -> bool:
        """Returns True if a face is detected looking at the camera or engagement forced."""
        if self.force_engaged:
            return True
        if not self.cap or not self.face_cascade:
            return False

        ret, frame = self.cap.read()
        if not ret:
            return False

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        return len(faces) > 0

    def listen(self, timeout_s: float = 6.0) -> str:
        """Listens to microphone using Vosk and returns the transcribed text."""
        print("Listening...")
        if not self.stream or not self.recognizer:
            return ""

        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                data = self.stream.read(4000, exception_on_overflow=False)
            except Exception:
                break
            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "")
                if text:
                    return text
        try:
            partial = json.loads(self.recognizer.PartialResult()).get("partial", "")
            return partial
        except Exception:
            return ""

    def analyze_scene(self) -> List[str]:
        """Captures a frame and queries local Moondream vision model via Ollama."""
        if not self.cap or not cv2:
            return []

        ret, frame = self.cap.read()
        if not ret:
            return []

        _, buffer = cv2.imencode(".jpg", frame)
        frame_base64 = base64.b64encode(buffer).decode("utf-8")

        payload = {
            "model": self.vision_model,
            "prompt": "List the main objects in this scene as a comma separated list.",
            "images": [frame_base64],
            "stream": False,
        }

        try:
            response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=self.timeout_s)
            response.raise_for_status()
            data = response.json()
            objects_str = data.get("response", "")
            return [obj.strip() for obj in objects_str.split(",") if obj.strip()]
        except Exception as exc:
            print(f"Failed to query {self.vision_model} via Ollama: {exc}")
            return []

    def cleanup(self) -> None:
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        if self.audio:
            try:
                self.audio.terminate()
            except Exception:
                pass
            self.audio = None
