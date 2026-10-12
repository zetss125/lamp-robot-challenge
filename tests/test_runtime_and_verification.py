import json
import time
import unittest

from main import InteractionRuntime
from protocol import BodyCommand, BodyResult


class FakePerception:
    def __init__(self, engaged=True, speech="", objects=None):
        self._engaged = engaged
        self._speech = speech
        self._objects = objects or []

    def check_engagement(self):
        return self._engaged

    def listen(self):
        return self._speech

    def analyze_scene(self):
        return list(self._objects)

    def cleanup(self):
        pass


class FakeBrain:
    def process(self, speech, scene_objects):
        return json.dumps({
            "speech": "I heard you.",
            "action": "neutral",
            "light": "warm",
            "sound": "none",
            "music": "none",
            "reason": "conversational",
        })


class FakeTransportClient:
    def __init__(self):
        self.commands = []
        self.last_command = None

    def send_command(self, command: BodyCommand) -> BodyResult:
        self.commands.append(command)
        self.last_command = command
        return BodyResult(
            seq=command.seq,
            goal_id=command.goal_id,
            accepted=True,
            completed=True,
            status="completed",
            started_at=time.monotonic(),
            finished_at=time.monotonic(),
            measurements={"action": command.action, "joint_error_rad": 0.02, "duration_ms": 50},
        )


class RuntimeAndVerificationTests(unittest.TestCase):
    def test_extract_goal_target(self):
        runtime = InteractionRuntime(FakePerception(), FakeBrain(), FakeTransportClient())

        is_goal, target = runtime.extract_goal_target("where is my coffee mug")
        self.assertTrue(is_goal)
        self.assertEqual(target, "coffee mug")

        is_goal, target = runtime.extract_goal_target("can you see the yellow ball?")
        self.assertTrue(is_goal)
        self.assertEqual(target, "yellow ball")

        is_goal, target = runtime.extract_goal_target("hello how are you")
        self.assertFalse(is_goal)
        self.assertIsNone(target)

    def test_goal_directed_plans_search_when_target_missing(self):
        perception = FakePerception(engaged=True, speech="where is the red cup", objects=["laptop", "keyboard"])
        client = FakeTransportClient()
        runtime = InteractionRuntime(perception, FakeBrain(), client)

        record = runtime.run_once()

        self.assertIsNotNone(record)
        self.assertEqual(client.last_command.action, "search")
        self.assertEqual(client.last_command.light, "thinking")
        self.assertEqual(client.last_command.sound, "chirp")
        self.assertEqual(client.last_command.music, "curious")

    def test_goal_directed_acknowledges_when_target_already_present(self):
        perception = FakePerception(engaged=True, speech="where is the red cup", objects=["laptop", "red cup"])
        client = FakeTransportClient()
        runtime = InteractionRuntime(perception, FakeBrain(), client)

        record = runtime.run_once()

        self.assertIsNotNone(record)
        self.assertEqual(client.last_command.action, "nod")
        self.assertEqual(client.last_command.light, "success")
        self.assertEqual(client.last_command.sound, "confirm")
        self.assertEqual(client.last_command.music, "success")

    def test_completion_verification_target_found(self):
        runtime = InteractionRuntime(FakePerception(), FakeBrain(), FakeTransportClient())

        pre = {"timestamp": 100.0, "engaged": True, "objects": ["desk"]}
        post = {"timestamp": 101.0, "engaged": True, "objects": ["desk", "red cup"]}
        body_res = {
            "accepted": True,
            "completed": True,
            "measurements": {"joint_error_rad": 0.01, "duration_ms": 100},
        }

        ver = runtime.verify_completion("find my red cup", "red cup", "search", pre, post, body_res)

        self.assertTrue(ver["completed"])
        self.assertTrue(ver["goal_satisfied"])
        self.assertTrue(ver["target_in_post"])
        self.assertFalse(ver["target_in_pre"])

    def test_completion_verification_target_missing_fails_goal(self):
        runtime = InteractionRuntime(FakePerception(), FakeBrain(), FakeTransportClient())

        pre = {"timestamp": 100.0, "engaged": True, "objects": ["desk"]}
        post = {"timestamp": 101.0, "engaged": True, "objects": ["desk"]}
        body_res = {
            "accepted": True,
            "completed": True,
            "measurements": {"joint_error_rad": 0.01, "duration_ms": 100},
        }

        ver = runtime.verify_completion("find my red cup", "red cup", "search", pre, post, body_res)

        self.assertFalse(ver["completed"])
        self.assertFalse(ver["goal_satisfied"])
        self.assertEqual(ver["reason"], "target_not_found_after_search")

    def test_runtime_stop_coordination(self):
        perception = FakePerception(engaged=True, speech="hello", objects=["desk"])
        client = FakeTransportClient()
        runtime = InteractionRuntime(perception, FakeBrain(), client)

        runtime.stop()
        self.assertTrue(runtime.is_stopped)
        record = runtime.run_once()
        self.assertIsNone(record)
        self.assertEqual(len(client.commands), 0)


if __name__ == "__main__":
    unittest.main()
