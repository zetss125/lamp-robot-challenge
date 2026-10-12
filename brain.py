import json
import requests

from protocol import safe_intent

class BrainModule:
    def __init__(self, ollama_url="http://localhost:11434", model="qwen2:0.5b", timeout_s=12):
        self.ollama_url = ollama_url
        self.model = model
        self.timeout_s = timeout_s
        self.memory = []
        self.system_prompt = """You are a helpful, curious lamp robot. 
You are speaking to a user. Be concise. 
Always output your response in STRICT JSON format like this:
{"speech": "your spoken text here", "action": "one of: neutral, nod, shake_head, look_left, look_right, search", "light": "one of: off, warm, thinking, success, error", "sound": "one of: none, chirp, confirm, error", "music": "one of: none, curious, success", "reason": "brief reason"}"""

    def process(self, spoken_text, scene_objects):
        # Update short term memory
        self.memory.append({"role": "user", "content": f"User said: {spoken_text}"})
        if scene_objects:
            self.memory.append({"role": "system", "content": f"I currently see: {', '.join(scene_objects)}"})
            
        # Keep memory bounded to last 10 messages to save context and speed
        if len(self.memory) > 10:
            self.memory = self.memory[-10:]
            
        messages = [{"role": "system", "content": self.system_prompt}] + self.memory
        
        payload = {
            "model": self.model,
            "messages": messages,
            "format": "json",
            "stream": False
        }
        
        try:
            response = requests.post(f"{self.ollama_url}/api/chat", json=payload, timeout=self.timeout_s)
            response.raise_for_status()
            data = response.json()
            
            # Extract response text (which is guaranteed JSON by ollama's format parameter)
            response_json_str = data.get("message", {}).get("content", "{}")
            intent = safe_intent(response_json_str)
            response_json_str = json.dumps(intent)
            
            # Store our own response in memory
            self.memory.append({"role": "assistant", "content": response_json_str})
            
            return response_json_str
            
        except Exception as e:
            print(f"Failed to query {self.model} via Ollama:", e)
            # Fallback intent if the model fails
            return json.dumps({
                "speech": "I am having trouble thinking right now.",
                "action": "shake_head",
                "light": "error",
                "sound": "error",
                "music": "none",
                "reason": "model request failed"
            })
