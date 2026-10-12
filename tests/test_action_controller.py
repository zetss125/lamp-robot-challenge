import time
import unittest

from action_controller import ActionController
from protocol import BodyCommand


class FakeSimulation:
    def __init__(self):
        self.joint_angles = [0.0, 0.0, 0.0, 0.0, 0.0]
        self.light_color = (0.0, 0.0, 0.0)
        self.step_count = 0

    def set_joint_angles(self, angles):
        self.joint_angles = list(angles)

    def get_joint_angles(self):
        return list(self.joint_angles)

    def set_light(self, color):
        self.light_color = color

    def step(self):
        self.step_count += 1


class ActionControllerTests(unittest.TestCase):
    def test_execute_command_success(self):
        sim = FakeSimulation()
        ctrl = ActionController(simulation=sim)
        cmd = BodyCommand(
            seq=1,
            goal_id="g1",
            action="nod",
            light="success",
            sound="confirm",
            music="success",
            timeout_s=5.0,
        )

        res = ctrl.execute_command(cmd)

        self.assertTrue(res["completed"])
        self.assertFalse(res["timed_out"])
        self.assertEqual(res["action"], "nod")
        self.assertEqual(res["light"], "success")
        self.assertAlmostEqual(sim.light_color[0], ctrl.light_colors["success"][0])
        # After execution, reset back to neutral
        self.assertEqual(sim.joint_angles, ctrl.animations["neutral"])
        ctrl.cleanup()

    def test_pcm_tone_synthesis_linux_safe(self):
        ctrl = ActionController(simulation=None)
        # Verify tone synthesis logic does not raise exceptions
        played = ctrl._play_pcm_tone_linux(440, 0.01)
        # Should be a boolean (True if audio device or aplay played, False if skipped)
        self.assertIsInstance(played, bool)
        ctrl.cleanup()


if __name__ == "__main__":
    unittest.main()
