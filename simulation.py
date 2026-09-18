import pybullet as p
import pybullet_data
import time

class Simulation:
    def __init__(self, urdf_path):
        self.urdf_path = urdf_path
        self.client = p.connect(p.GUI)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        self.planeId = p.loadURDF("plane.urdf")
        
        # Load the dummy lamp
        self.robotId = p.loadURDF(self.urdf_path, [0, 0, 0], useFixedBase=True)
        
        self.num_joints = p.getNumJoints(self.robotId)
        self.joint_indices = []
        for i in range(self.num_joints):
            info = p.getJointInfo(self.robotId, i)
            if info[2] == p.JOINT_REVOLUTE:
                self.joint_indices.append(i)

    def set_joint_angles(self, target_angles):
        for i, target in zip(self.joint_indices, target_angles):
            p.setJointMotorControl2(
                bodyUniqueId=self.robotId,
                jointIndex=i,
                controlMode=p.POSITION_CONTROL,
                targetPosition=target,
                force=500
            )

    def step(self):
        p.stepSimulation()
        time.sleep(1./240.)

if __name__ == "__main__":
    sim = Simulation("robot/dummy_lamp_5dof.urdf")
    while True:
        sim.step()
