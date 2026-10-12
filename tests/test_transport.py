import json
import time
import unittest

from body_receiver import AuthoritativeBodyReceiver
from protocol import BodyCommand
from transport import BodyTransportClient, BodyTransportServer


class FakeActionController:
    def __init__(self):
        self.commands = []

    def execute_command(self, command):
        self.commands.append(command)
        return {
            "completed": True,
            "timed_out": False,
            "action": command.action,
            "duration_ms": 12,
            "joint_error_rad": 0.01,
            "light": command.light,
            "sound": command.sound,
            "music": command.music,
        }


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.action_controller = FakeActionController()
        self.receiver = AuthoritativeBodyReceiver(self.action_controller)
        # Use dynamic port (0) for test isolation
        self.server = BodyTransportServer(self.receiver, host="127.0.0.1", port=0)
        self.server.start()
        self.client = BodyTransportClient(host="127.0.0.1", port=self.server.bound_port, timeout_s=5.0)

    def tearDown(self):
        self.server.stop(timeout=1.0)

    def test_client_server_round_trip(self):
        cmd = BodyCommand(
            seq=1,
            goal_id="goal-transport-1",
            action="look_left",
            light="thinking",
            sound="chirp",
            music="curious",
        )
        result = self.client.send_command(cmd)

        self.assertEqual(result.seq, 1)
        self.assertEqual(result.goal_id, "goal-transport-1")
        self.assertTrue(result.accepted)
        self.assertTrue(result.completed)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.measurements.get("action"), "look_left")
        self.assertEqual(len(self.action_controller.commands), 1)

    def test_out_of_order_rejected_over_transport(self):
        cmd = BodyCommand(
            seq=5,  # Expected seq is 1
            goal_id="goal-out-of-order",
            action="nod",
        )
        result = self.client.send_command(cmd)

        self.assertFalse(result.accepted)
        self.assertFalse(result.completed)
        self.assertIn("expected seq 1", result.status)

    def test_transport_error_handling_when_server_unreachable(self):
        # Point client to a port with no listener
        dead_client = BodyTransportClient(host="127.0.0.1", port=59999, timeout_s=0.5)
        cmd = BodyCommand(seq=1, goal_id="goal-dead", action="nod")
        result = dead_client.send_command(cmd)

        self.assertFalse(result.accepted)
        self.assertIn("transport_error", result.status)


if __name__ == "__main__":
    unittest.main()
