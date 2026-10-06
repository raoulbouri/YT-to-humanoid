"""Shared helpers for comparing the human (SMPL joints streamed to SONIC) with the robot (forward kinematics of the logged joints).

Everything here is rotation-invariant or expressed in a pelvis-yaw frame, so the two skeletons can be compared even though
their proportions and global headings differ. Needs numpy + mujoco (the SONIC sim env has both).
"""
import os
import numpy as np
import mujoco

DEFAULT_SCENE = os.path.join(os.environ.get("SONIC_WORK", "."),
                             "repos/GR00T-WholeBodyControl/gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml")

_LEG = ["hip_pitch", "hip_roll", "hip_yaw", "knee", "ankle_pitch", "ankle_roll"]
_ARM = ["shoulder_pitch", "shoulder_roll", "shoulder_yaw", "elbow", "wrist_roll", "wrist_pitch", "wrist_yaw"]
# Order of the 29 body joints in the deploy's debug stream (body_q, last_action).
JOINT_NAMES = ([f"left_{n}_joint" for n in _LEG] + [f"right_{n}_joint" for n in _LEG]
               + ["waist_yaw_joint", "waist_roll_joint", "waist_pitch_joint"]
               + [f"left_{n}_joint" for n in _ARM] + [f"right_{n}_joint" for n in _ARM])
KEYPOINT_BODIES = {"pelvis": "pelvis", "lhip": "left_hip_pitch_link", "rhip": "right_hip_pitch_link",
                   "lknee": "left_knee_link", "rknee": "right_knee_link", "lank": "left_ankle_pitch_link",
                   "rank": "right_ankle_pitch_link", "lsho": "left_shoulder_pitch_link", "rsho": "right_shoulder_pitch_link",
                   "lelb": "left_elbow_link", "relb": "right_elbow_link", "lwri": "left_wrist_roll_link",
                   "rwri": "right_wrist_roll_link"}
# The same keypoints in the standard SMPL-24 order.
SMPL_IDX = {"pelvis": 0, "lhip": 1, "rhip": 2, "lknee": 4, "rknee": 5, "lank": 7, "rank": 8, "lsho": 16, "rsho": 17,
            "lelb": 18, "relb": 19, "lwri": 20, "rwri": 21}
UP = np.array([0.0, 0.0, 1.0])


class RobotFK:
    """G1 forward kinematics in MuJoCo from the logged joint angles and IMU quaternion (w, x, y, z)."""

    def __init__(self, scene=None):
        self.m = mujoco.MjModel.from_xml_path(scene or DEFAULT_SCENE)
        self.d = mujoco.MjData(self.m)
        self.qadr = [self.m.jnt_qposadr[mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_JOINT, n)] for n in JOINT_NAMES]
        self.bid = {k: mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, b) for k, b in KEYPOINT_BODIES.items()}

    def keypoints(self, q, quat):
        d = self.d
        d.qpos[:] = self.m.qpos0
        d.qpos[0:3] = 0
        d.qpos[3:7] = quat
        for adr, v in zip(self.qadr, q):
            d.qpos[adr] = v
        mujoco.mj_kinematics(self.m, d)
        return {k: d.xpos[i].copy() for k, i in self.bid.items()}


def human_keypoints(smpl24):
    return {k: smpl24[i] for k, i in SMPL_IDX.items()}


def _angle(a, b):
    c = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


def limb_angles(K):
    """Elbow/knee flexion, shoulder elevation, hip flexion (left/right) and torso lean, in degrees."""
    up = (K["lsho"] + K["rsho"]) / 2 - K["pelvis"]
    out = {}
    for s in "lr":
        out[f"{s}_elbow_flex"] = 180 - _angle(K[s + "sho"] - K[s + "elb"], K[s + "wri"] - K[s + "elb"])
        out[f"{s}_knee_flex"] = 180 - _angle(K[s + "hip"] - K[s + "knee"], K[s + "ank"] - K[s + "knee"])
        out[f"{s}_shoulder_elev"] = _angle(K[s + "elb"] - K[s + "sho"], -up)
        out[f"{s}_hip_flex"] = _angle(K[s + "knee"] - K[s + "hip"], -up)
    out["torso_lean"] = _angle(up, UP)
    return out


def pelvis_axes(lhip, rhip):
    """(forward, left, up) unit vectors of the pelvis-yaw frame (heading from the hip line, gravity-aligned)."""
    y = np.array([*(lhip - rhip)[:2], 0.0])
    y /= np.linalg.norm(y) + 1e-9
    return np.cross(y, UP), y, UP


def hand_positions(K):
    """Wrist position relative to the pelvis in the pelvis-yaw frame, normalised by arm length."""
    x, y, z = pelvis_axes(K["lhip"], K["rhip"])
    out = {}
    for s in "lr":
        arm = np.linalg.norm(K[s + "elb"] - K[s + "sho"]) + np.linalg.norm(K[s + "wri"] - K[s + "elb"])
        v = K[s + "wri"] - K["pelvis"]
        out[s] = np.array([v @ x, v @ y, v @ z]) / arm
    return out


def torso_angles(K):
    """Torso pitch (forward +), roll and twist (shoulder line vs hip line), degrees."""
    x, y, z = pelvis_axes(K["lhip"], K["rhip"])
    up = (K["lsho"] + K["rsho"]) / 2 - K["pelvis"]
    sh, hip = K["lsho"] - K["rsho"], K["lhip"] - K["rhip"]
    return (np.degrees(np.arctan2(up @ x, up @ z)), np.degrees(np.arctan2(up @ y, up @ z)),
            np.degrees(np.arctan2(sh[0] * hip[1] - sh[1] * hip[0], sh[0] * hip[0] + sh[1] * hip[1])))


def human_series(c, fn):
    return [fn(human_keypoints(c["smpl_joints"][i])) for i in range(len(c["pose_t"]))]


def robot_series(c, fk, fn):
    return [fn(fk.keypoints(c["body_q"][i], c["base_quat"][i])) for i in range(len(c["state_t"]))]


def angle_table(c, fk):
    """(names, human (n_pose, 9), robot (n_state, 9)) limb angles for a capture.npz."""
    h = human_series(c, limb_angles)
    names = list(h[0])
    robot = robot_series(c, fk, limb_angles)
    return (names, np.array([[x[k] for k in names] for x in h]), np.array([[x[k] for k in names] for x in robot]))


def resample(t_pose, t_state, series, lag):
    """Robot series (n_state, k) sampled at the pose timestamps + lag."""
    return np.stack([np.interp(t_pose + lag, t_state, series[:, j]) for j in range(series.shape[1])], 1)
