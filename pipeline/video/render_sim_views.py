"""Re-render the simulated G1 (MuJoCo) from LOGGED state: measured joint angles + IMU orientation (capture.npz).
Writes front.mp4 and side.mp4 (same trajectory, exactly in sync). Root x/y fixed at 0 (SONIC commands no translation);
root height from keeping the lowest ankle on the floor. Cameras follow the robot heading (smoothed) by default.
Output frame j shows the robot state at (stream_start + j/fps + lag)."""
import argparse, subprocess, numpy as np, mujoco, os
ap = argparse.ArgumentParser()
ap.add_argument("--capture", required=True); ap.add_argument("--out-prefix", required=True)
ap.add_argument("--fps", type=float, default=30); ap.add_argument("--seconds", type=float, required=True)
ap.add_argument("--lag", type=float, default=0.0, help="seconds added to the sampling time (compensates pipeline latency)")
ap.add_argument("--width", type=int, default=960); ap.add_argument("--height", type=int, default=540)
ap.add_argument("--distance", type=float, default=2.3); ap.add_argument("--elevation", type=float, default=-8.0)
ap.add_argument("--scene", default=None, help="G1 scene xml (default: the SONIC checkout under $SONIC_WORK)")
ap.add_argument("--fixed-heading", action="store_true", help="world-fixed cameras (relative to the initial heading) instead of heading-following")
a = ap.parse_args()
SCENE = a.scene or os.path.join(os.environ.get("SONIC_WORK", "."), "repos/GR00T-WholeBodyControl/gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml")
m = mujoco.MjModel.from_xml_path(SCENE); m.vis.global_.offwidth = max(m.vis.global_.offwidth, a.width); m.vis.global_.offheight = max(m.vis.global_.offheight, a.height); d = mujoco.MjData(m)
c = np.load(a.capture); st = c["state_t"]; bq = c["body_q"]; qu = c["base_quat"]; t0 = c["pose_t"][0]
L = ["left_hip_pitch","left_hip_roll","left_hip_yaw","left_knee","left_ankle_pitch","left_ankle_roll"]; R_ = [n.replace("left", "right") for n in L]
arm = ["shoulder_pitch","shoulder_roll","shoulder_yaw","elbow","wrist_roll","wrist_pitch","wrist_yaw"]
names = [n + "_joint" for n in L + R_ + ["waist_yaw","waist_roll","waist_pitch"] + ["left_" + x for x in arm] + ["right_" + x for x in arm]]
qadr = [m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)] for n in names]
bid = lambda n: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, n)
LA, RA = bid("left_ankle_roll_link"), bid("right_ankle_roll_link")
# sole offset: ankle height above the floor in the model default pose
d.qpos[:] = m.qpos0; mujoco.mj_kinematics(m, d); c_off = min(d.xpos[LA][2], d.xpos[RA][2])
def yaw_of(q): w, x, y, z = q; return np.degrees(np.arctan2(2*(w*z + x*y), 1 - 2*(y*y + z*z)))
yaw = np.degrees(np.unwrap(np.radians([yaw_of(q) for q in qu])))
k = max(1, int(0.2 / np.median(np.diff(st)))); yaw_s = np.convolve(np.pad(yaw, (k, k), mode="edge"), np.ones(2*k+1) / (2*k+1), mode="valid")
yaw0 = float(np.median(yaw[(st >= t0) & (st <= t0 + 1.0)])) if ((st >= t0) & (st <= t0 + 1.0)).any() else float(yaw[0])
def interp(arr, t): return np.array([np.interp(t, st, arr[:, j]) for j in range(arr.shape[1])])
def pose_at(t):
    q = interp(qu, t); q /= np.linalg.norm(q); ang = interp(bq, t)
    d.qpos[:] = m.qpos0; d.qpos[0:3] = [0, 0, 0]; d.qpos[3:7] = q
    for adr, v in zip(qadr, ang): d.qpos[adr] = v
    mujoco.mj_kinematics(m, d); rel = min(d.xpos[LA][2], d.xpos[RA][2])
    d.qpos[2] = c_off - rel; mujoco.mj_forward(m, d)
    return float(np.interp(t, st, yaw_s))
r = mujoco.Renderer(m, a.height, a.width)
opt = mujoco.MjvOption(); opt.sitegroup[:] = 0   # hide the red COM marker site
cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE; cam.distance = a.distance; cam.elevation = a.elevation
n = int(round(a.seconds * a.fps)); os.makedirs(os.path.dirname(a.out_prefix) or ".", exist_ok=True)
procs = {}
for view, off in [("front", 180.0), ("side", 90.0)]:
    procs[view] = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{a.width}x{a.height}", "-r", str(a.fps), "-i", "-",
                                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", f"{a.out_prefix}_{view}.mp4"], stdin=subprocess.PIPE)
for j in range(n):
    t = t0 + j / a.fps + a.lag
    psi = pose_at(t); psi_use = yaw0 if a.fixed_heading else psi
    for view, off in [("front", 180.0), ("side", 90.0)]:
        cam.azimuth = psi_use + off; cam.lookat[:] = [0, 0, 0.62]
        r.update_scene(d, camera=cam, scene_option=opt); procs[view].stdin.write(r.render().tobytes())
for p in procs.values(): p.stdin.close(); p.wait()
print("rendered", n, "frames per view; initial yaw %.1f deg; yaw span %.1f deg; floor offset %.3f" % (yaw0, yaw_s.max() - yaw_s.min(), c_off))
