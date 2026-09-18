import json
import requests

class BrainModule:
    def __init__(self, ollama_url="http://localhost:11434"):
        self.ollama_url = ollama_url
        self.memory = []
        self.system_prompt = """You are a helpful, curious lamp robot. 
You are speaking to a user. Be concise. 
Always output your response in STRICT JSON format like this:
{"speech": "your spoken text here", "action": "one of: neutral, nod, shake_head, look_left, look_right, search"}"""

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
            "model": "phi3:mini",
            "messages": messages,
            "format": "json",
            "stream": False
        }
        
        try:
            response = requests.post(f"{self.ollama_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Extract response text (which is guaranteed JSON by ollama's format parameter)
            response_json_str = data.get("message", {}).get("content", "{}")
            
            # Store our own response in memory
            self.memory.append({"role": "assistant", "content": response_json_str})
            
            return response_json_str
            
        except Exception as e:
            print("Failed to query Phi-3 via Ollama:", e)
            # Fallback intent if the model fails
            return json.dumps({
                "speech": "I am having trouble thinking right now.",
                "action": "shake_head"
            })
