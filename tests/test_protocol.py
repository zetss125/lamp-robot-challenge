import json
import unittest

from protocol import (
    ALLOWED_ACTIONS,
    ALLOWED_LIGHTS,
    ALLOWED_MUSIC,
    ALLOWED_SOUNDS,
    BodyCommand,
    BodyResult,
    command_from_intent,
    safe_intent,
)


class ProtocolTests(unittest.TestCase):
    def test_body_command_round_trips_json(self):
        command = BodyCommand(
            seq=1,
            goal_id="goal-1",
            action="nod",
            speech="hello",
            light="success",
            sound="confirm",
            music="success",
            timeout_s=5.0,
        )

        decoded = BodyCommand.from_json(command.to_json())

        self.assertEqual(decoded.seq, 1)
        self.assertEqual(decoded.goal_id, "goal-1")
        self.assertEqual(decoded.action, "nod")
        self.assertEqual(decoded.speech, "hello")
        self.assertEqual(decoded.light, "success")
        self.assertEqual(decoded.sound, "confirm")
        self.assertEqual(decoded.music, "success")
        self.assertEqual(decoded.timeout_s, 5.0)

    def test_rejects_unsupported_action(self):
        command = BodyCommand(seq=1, goal_id="goal-1", action="wave")
        with self.assertRaises(ValueError):
            command.validate()

    def test_rejects_invalid_timeouts(self):
        with self.assertRaises(ValueError):
            BodyCommand(seq=1, goal_id="goal-1", timeout_s=-1.0).validate()
        with self.assertRaises(ValueError):
            BodyCommand(seq=1, goal_id="goal-1", timeout_s=0.0).validate()
        with self.assertRaises(ValueError):
            BodyCommand(seq=1, goal_id="goal-1", timeout_s=35.0).validate()

    def test_safe_intent_clamps_invalid_model_output(self):
        intent = safe_intent(json.dumps({"speech": "ok", "action": "raw_joint_move", "light": "laser"}))
        self.assertEqual(intent["action"], "shake_head")
        self.assertEqual(intent["light"], "error")

    def test_command_from_intent_includes_effects_and_timeout(self):
        command = command_from_intent(
            2,
            "goal-2",
            {"speech": "found it", "action": "search", "light": "thinking", "sound": "chirp", "music": "curious", "timeout_s": 10.0},
        )
        self.assertEqual(command.seq, 2)
        self.assertEqual(command.sound, "chirp")
        self.assertEqual(command.music, "curious")
        self.assertEqual(command.timeout_s, 10.0)

    def test_body_result_serialization(self):
        res = BodyResult(
            seq=1,
            goal_id="g1",
            accepted=True,
            completed=True,
            status="completed",
            started_at=100.0,
            finished_at=101.5,
            measurements={"duration_ms": 1500, "joint_error_rad": 0.02},
        )
        data = json.loads(res.to_json())
        self.assertTrue(data["accepted"])
        self.assertTrue(data["completed"])
        self.assertEqual(data["measurements"]["duration_ms"], 1500)


if __name__ == "__main__":
    unittest.main()
