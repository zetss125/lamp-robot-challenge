import os
import time
from typing import Dict, List, Optional

try:
    import pybullet as p
    import pybullet_data
except ImportError:
    p = None
    pybullet_data = None


class Simulation:
    def __init__(self, urdf_path: str, gui: bool = True):
        self.urdf_path = urdf_path
        self.client = None
        self.planeId = None
        self.robotId = None
        self.num_joints = 0
        self.joint_indices: List[int] = []
        self.link_indices: Dict[str, int] = {}
        self.light_link: Optional[int] = None

        if not p or not pybullet_data:
            print("Notice: PyBullet is not installed in the current environment; running in stub mode.")
            return

        mode = p.GUI if gui and os.environ.get("PYBULLET_DIRECT") != "1" else p.DIRECT
        self.client = p.connect(mode)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        self.planeId = p.loadURDF("plane.urdf")

        # Load the dummy lamp
        self.robotId = p.loadURDF(self.urdf_path, [0, 0, 0], useFixedBase=True)

        self.num_joints = p.getNumJoints(self.robotId)
        for i in range(self.num_joints):
            info = p.getJointInfo(self.robotId, i)
            self.link_indices[info[12].decode("utf-8")] = i
            if info[2] == p.JOINT_REVOLUTE:
                self.joint_indices.append(i)
        self.light_link = self.link_indices.get("light_emitter_link")

    def set_joint_angles(self, target_angles: List[float]) -> None:
        if not p or self.robotId is None:
            return
        for i, target in zip(self.joint_indices, target_angles):
            p.setJointMotorControl2(
                bodyUniqueId=self.robotId,
                jointIndex=i,
                controlMode=p.POSITION_CONTROL,
                targetPosition=target,
                force=500,
            )

    def get_joint_angles(self) -> List[float]:
        if not p or self.robotId is None:
            return []
        return [p.getJointState(self.robotId, i)[0] for i in self.joint_indices]

    def set_light(self, rgb, alpha: float = 1.0) -> None:
        if not p or self.robotId is None or self.light_link is None:
            return
        p.changeVisualShape(
            self.robotId,
            self.light_link,
            rgbaColor=[float(rgb[0]), float(rgb[1]), float(rgb[2]), float(alpha)],
        )

    def step(self) -> None:
        if not p:
            time.sleep(1.0 / 240.0)
            return
        p.stepSimulation()
        time.sleep(1.0 / 240.0)

    def step_for(self, seconds: float) -> None:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.step()

    def cleanup(self) -> None:
        if p and self.client is not None and p.isConnected(self.client):
            p.disconnect(self.client)


if __name__ == "__main__":
    sim = Simulation("robot/dummy_lamp_5dof.urdf")
    try:
        while True:
            sim.step()
    finally:
        sim.cleanup()
