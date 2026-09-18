import pyttsx3
import json

class ActionController:
    def __init__(self, simulation=None):
        self.sim = simulation
        self.tts_engine = pyttsx3.init()
        # Set to a recognizable voice
        voices = self.tts_engine.getProperty('voices')
        if voices:
            self.tts_engine.setProperty('voice', voices[0].id)
            
        # Define basic animations as joint target arrays
        # [base_yaw, shoulder_pitch, elbow_pitch, neck_yaw, head_pitch]
        self.animations = {
            "neutral": [0.0, 0.0, -0.5, 0.0, 0.0],
            "nod": [0.0, 0.2, -0.5, 0.0, -0.4],
            "shake_head": [0.0, 0.0, -0.5, 0.5, 0.0],
            "look_left": [0.5, 0.0, -0.5, 0.0, 0.0],
            "look_right": [-0.5, 0.0, -0.5, 0.0, 0.0],
            "search": [0.0, -0.3, -0.2, 0.8, -0.2],
        }

    def execute_intent(self, intent_json_str):
        try:
            intent = json.loads(intent_json_str)
            action = intent.get("action", "neutral")
            speech = intent.get("speech", "")
            
            if action in self.animations and self.sim:
                print(f"Executing action: {action}")
                self.sim.set_joint_angles(self.animations[action])
            
            if speech:
                print(f"Robot says: {speech}")
                self.tts_engine.say(speech)
                self.tts_engine.runAndWait()
                
            # Return to neutral after speaking
            if self.sim:
                self.sim.set_joint_angles(self.animations["neutral"])
                
        except json.JSONDecodeError:
            print("Failed to parse intent JSON")

