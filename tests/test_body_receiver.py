import json
import unittest

from body_receiver import AuthoritativeBodyReceiver
from protocol import BodyCommand


class FakeActionController:
    def __init__(self, should_timeout=False, should_fail=False):
        self.commands = []
        self.should_timeout = should_timeout
        self.should_fail = should_fail

    def execute_command(self, command):
        self.commands.append(command)
        if self.should_fail:
            raise RuntimeError("Hardware actuator error")
        return {
            "completed": not self.should_timeout,
            "timed_out": self.should_timeout,
            "action": command.action,
            "duration_ms": 5000 if self.should_timeout else 100,
            "joint_error_rad": 0.01,
            "light": command.light,
            "sound": command.sound,
            "music": command.music,
        }


class BodyReceiverTests(unittest.TestCase):
    def test_accepts_in_order_command_and_returns_telemetry(self):
        receiver = AuthoritativeBodyReceiver(FakeActionController())
        command = BodyCommand(seq=1, goal_id="goal-1", action="nod")

        result = json.loads(receiver.handle(command.to_json()))

        self.assertTrue(result["accepted"])
        self.assertTrue(result["completed"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["measurements"]["action"], "nod")

    def test_rejects_out_of_order_command(self):
        receiver = AuthoritativeBodyReceiver(FakeActionController())
        command = BodyCommand(seq=2, goal_id="goal-1", action="nod")

        result = json.loads(receiver.handle(command.to_json()))

        self.assertFalse(result["accepted"])
        self.assertIn("expected seq 1", result["status"])

    def test_handles_timeout_telemetry(self):
        receiver = AuthoritativeBodyReceiver(FakeActionController(should_timeout=True))
        command = BodyCommand(seq=1, goal_id="goal-timeout", action="search")

        result = json.loads(receiver.handle(command.to_json()))

        self.assertTrue(result["accepted"])
        self.assertFalse(result["completed"])
        self.assertEqual(result["status"], "timed_out")

    def test_handles_hardware_failure_gracefully(self):
        receiver = AuthoritativeBodyReceiver(FakeActionController(should_fail=True))
        command = BodyCommand(seq=1, goal_id="goal-err", action="shake_head")

        result = json.loads(receiver.handle(command.to_json()))

        self.assertTrue(result["accepted"])
        self.assertFalse(result["completed"])
        self.assertEqual(result["status"], "failed")
        self.assertIn("Hardware actuator error", result["errors"][0])


if __name__ == "__main__":
    unittest.main()
