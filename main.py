import time
import threading
from perception import PerceptionModule
from brain import BrainModule
from action_controller import ActionController
from simulation import Simulation

def perception_cognition_loop(perception, brain, action_ctrl):
    print("Starting perception and cognition loop...")
    while True:
        # 1. Check engagement
        if perception.check_engagement():
            # 2. Listen for speech
            user_speech = perception.listen()
            print(f"Heard: {user_speech}")
            
            # 3. Analyze scene memory
            scene_objects = perception.analyze_scene()
            
            # 4. Generate response and action intent
            intent_json = brain.process(user_speech, scene_objects)
            
            # 5. Execute action and speech
            action_ctrl.execute_intent(intent_json)
            
        time.sleep(1) # run at 1Hz for this demo loop

if __name__ == "__main__":
    # Initialize Simulation
    sim = Simulation("robot/dummy_lamp_5dof.urdf")
    
    # Initialize Modules
    perception = PerceptionModule()
    brain = BrainModule()
    action_ctrl = ActionController(simulation=sim)
    
    # Force a mock engagement for the sake of the demo loop
    perception.face_detected = True
    
    # Start the cognition loop in a separate thread so PyBullet can step in main thread
    cognition_thread = threading.Thread(
        target=perception_cognition_loop, 
        args=(perception, brain, action_ctrl),
        daemon=True
    )
    cognition_thread.start()
    
    # PyBullet must step in the main thread
    print("Starting simulation loop...")
    try:
        while True:
            sim.step()
    except KeyboardInterrupt:
        print("Shutting down...")
        perception.cleanup()

