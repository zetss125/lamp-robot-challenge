import json
import os
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from action_controller import ActionController
from body_receiver import AuthoritativeBodyReceiver
from brain import BrainModule
from perception import PerceptionModule
from protocol import command_from_intent, safe_intent
from simulation import Simulation
from transport import BodyTransportClient, BodyTransportServer


MEASUREMENTS_PATH = "measurements.jsonl"


class InteractionRuntime:
    """Laptop-side observe-act-reobserve runtime communicating with the body over a transport boundary."""

    def __init__(self, perception: PerceptionModule, brain: BrainModule, transport_client: BodyTransportClient):
        self.perception = perception
        self.brain = brain
        self.transport_client = transport_client
        self.seq = 1
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    @property
    def is_stopped(self) -> bool:
        return self._stop_event.is_set()

    def observe(self) -> Dict[str, Any]:
        return {
            "timestamp": time.time(),
            "engaged": self.perception.check_engagement(),
            "objects": self.perception.analyze_scene(),
        }

    def run_once(self) -> Optional[Dict[str, Any]]:
        if self._stop_event.is_set():
            return None

        pre = self.observe()
        if not pre["engaged"]:
            return None

        user_speech = self.perception.listen()
        if not user_speech:
            return None

        is_goal, target_object = self.extract_goal_target(user_speech)
        raw_brain_intent = self.brain.process(user_speech, pre.get("objects", []))
        intent = safe_intent(raw_brain_intent)

        if is_goal:
            intent = self._plan_goal_intent(intent, target_object, pre.get("objects", []))

        goal_id = str(uuid.uuid4())
        command = command_from_intent(self.seq, goal_id, intent)
        self.seq += 1

        # Send command across the transport boundary to the authoritative body receiver
        body_result_obj = self.transport_client.send_command(command)
        body_result = json.loads(body_result_obj.to_json())

        # Reobserve scene after body action execution
        post = self.observe()

        verification = self.verify_completion(
            user_speech=user_speech,
            target_object=target_object,
            action=command.action,
            pre=pre,
            post=post,
            body_result=body_result,
        )

        record = {
            "goal_id": goal_id,
            "timestamp": time.time(),
            "speech": user_speech,
            "is_goal_directed": is_goal,
            "target_object": target_object,
            "pre_observation": pre,
            "command": json.loads(command.to_json()),
            "body_result": body_result,
            "post_observation": post,
            "verification": verification,
        }
        self._append_measurement(record)
        return record

    def extract_goal_target(self, speech: str) -> Tuple[bool, Optional[str]]:
        """Extracts goal intent and referenced target object from speech."""
        text = speech.lower().strip()
        patterns = [
            r"(?:find|look for|where is|where's|can you find|can you see|point at|show me)\s+(?:a|an|the|my)?\s*([a-zA-Z0-9_\- ]+)",
            r"(?:do you see|is there)\s+(?:a|an|the|my)?\s*([a-zA-Z0-9_\- ]+)",
            r"(?:search for)\s+(?:a|an|the|my)?\s*([a-zA-Z0-9_\- ]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                raw_target = match.group(1).strip().rstrip(".?!")
                # Remove common filler words
                target = re.sub(r"^(a|an|the|my|some)\s+", "", raw_target).strip()
                if target:
                    return True, target

        goal_words = ("find", "look for", "point at", "search", "where is", "can you see", "locate")
        if any(w in text for w in goal_words):
            return True, None
        return False, None

    def _target_in_scene(self, target: Optional[str], objects: List[str]) -> bool:
        if not target:
            return bool(objects)
        target_clean = target.lower().strip()
        for obj in objects:
            obj_clean = obj.lower().strip()
            if target_clean in obj_clean or obj_clean in target_clean:
                return True
        return False

    def _plan_goal_intent(
        self,
        base_intent: Dict[str, Any],
        target_object: Optional[str],
        scene_objects: List[str],
    ) -> Dict[str, Any]:
        """Plans dynamic action based on visual evidence and target presence."""
        target_name = target_object if target_object else "target object"
        target_present = self._target_in_scene(target_object, scene_objects)

        if target_present:
            # Object already located in live visual evidence: acknowledge and orient
            base_intent["action"] = "nod"
            base_intent["light"] = "success"
            base_intent["sound"] = "confirm"
            base_intent["music"] = "success"
            base_intent["speech"] = f"I see the {target_name} right in front of me!"
            base_intent["reason"] = f"Target '{target_name}' confirmed present in visual observation."
        else:
            # Object not in initial view: execute active search/scan
            base_intent["action"] = "search"
            base_intent["light"] = "thinking"
            base_intent["sound"] = "chirp"
            base_intent["music"] = "curious"
            base_intent["speech"] = f"Looking around to locate the {target_name}."
            base_intent["reason"] = f"Target '{target_name}' not in pre-observation; searching scene."

        return base_intent

    def verify_completion(
        self,
        user_speech: str,
        target_object: Optional[str],
        action: str,
        pre: Dict[str, Any],
        post: Dict[str, Any],
        body_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Performs rigorous completion verification of body execution, scene reobservation, and goal state."""
        body_accepted = bool(body_result.get("accepted", False))
        body_completed = bool(body_result.get("completed", False)) and not body_result.get("measurements", {}).get("timed_out", False)
        joint_error = float(body_result.get("measurements", {}).get("joint_error_rad", 0.0))
        execution_valid = body_accepted and body_completed and (joint_error < 0.15)

        reobserved = bool(post is not None and "objects" in post and post.get("timestamp", 0) >= pre.get("timestamp", 0))

        is_goal = self.extract_goal_target(user_speech)[0]
        pre_objects = pre.get("objects", [])
        post_objects = post.get("objects", []) if post else []

        target_in_pre = self._target_in_scene(target_object, pre_objects) if target_object else None
        target_in_post = self._target_in_scene(target_object, post_objects) if target_object else None

        if is_goal:
            if target_object:
                goal_satisfied = bool(target_in_post or (target_in_pre and execution_valid))
                reason = "target_confirmed_present" if goal_satisfied else "target_not_found_after_search"
            else:
                goal_satisfied = execution_valid and reobserved
                reason = "goal_motion_and_reobservation_completed"
        else:
            goal_satisfied = execution_valid
            reason = "conversational_action_completed"

        completed = bool(execution_valid and reobserved and goal_satisfied)

        return {
            "completed": completed,
            "goal_satisfied": goal_satisfied,
            "body_completed": body_completed,
            "execution_valid": execution_valid,
            "reobserved": reobserved,
            "is_goal_directed": is_goal,
            "target_object": target_object,
            "target_in_pre": target_in_pre,
            "target_in_post": target_in_post,
            "action": action,
            "reason": reason,
        }

    def _append_measurement(self, record: Dict[str, Any]) -> None:
        try:
            with open(MEASUREMENTS_PATH, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        except Exception as exc:
            print(f"Warning: Failed to write measurement record: {exc}")


def perception_cognition_loop(runtime: InteractionRuntime, stop_event: threading.Event) -> None:
    print("Starting observe-act-reobserve cognition loop...")
    while not stop_event.is_set():
        try:
            runtime.run_once()
        except Exception as exc:
            print(f"Error in cognition step: {exc}")
        # Bounded sleep with interrupt check
        for _ in range(10):
            if stop_event.is_set():
                break
            time.sleep(0.1)


if __name__ == "__main__":
    stop_event = threading.Event()

    print("Initializing PyBullet simulation...")
    sim = Simulation("robot/dummy_lamp_5dof.urdf")

    print("Initializing action controller & authoritative body receiver...")
    action_ctrl = ActionController(simulation=sim)
    body_receiver = AuthoritativeBodyReceiver(action_ctrl)

    print("Starting Body Transport Server on TCP 127.0.0.1:8765...")
    transport_server = BodyTransportServer(receiver=body_receiver, host="127.0.0.1", port=8765)
    transport_server.start()

    print("Initializing laptop cognition modules (Perception, Brain, Transport Client)...")
    perception = PerceptionModule()
    brain = BrainModule()
    transport_client = BodyTransportClient(host="127.0.0.1", port=transport_server.bound_port)
    runtime = InteractionRuntime(perception, brain, transport_client)

    perception.force_engaged = os.environ.get("FORCE_ENGAGEMENT") == "1"

    cognition_thread = threading.Thread(
        target=perception_cognition_loop,
        args=(runtime, stop_event),
        name="CognitionThread",
        daemon=False,
    )
    cognition_thread.start()

    print("System active. Press Ctrl+C to shut down.")
    try:
        while not stop_event.is_set():
            sim.step()
    except KeyboardInterrupt:
        print("\nShutdown signal received...")
    finally:
        print("Stopping cognition thread...")
        stop_event.set()
        runtime.stop()
        cognition_thread.join(timeout=3.0)

        print("Stopping transport server...")
        transport_server.stop(timeout=2.0)

        print("Cleaning up perception and audio streams...")
        perception.cleanup()

        print("Cleaning up action controller...")
        action_ctrl.cleanup()

        print("Cleaning up PyBullet simulation...")
        sim.cleanup()

        print("Shutdown complete.")
