#!/usr/bin/env python
"""Torso tracking split into pitch (forward lean), roll (sideways lean) and twist, human vs robot, plus waist joint use.
usage: torso_analysis.py <capture.npz> <smpl_v3_frames.npz> <lag_s> [--scene scene.xml]"""
import argparse, numpy as np
import limb_angles as la

ap = argparse.ArgumentParser(); ap.add_argument("capture"); ap.add_argument("smpl"); ap.add_argument("lag", type=float); ap.add_argument("--scene")
a = ap.parse_args()
c = np.load(a.capture); fk = la.RobotFK(a.scene)
sm = np.load(a.smpl)["smpl_joints"].reshape(-1, 24, 3)
pt, st = c["pose_t"][:len(sm)], c["state_t"]
hum = np.array([la.torso_angles(la.human_keypoints(j)) for j in sm])
rob = np.array([la.torso_angles(fk.keypoints(c["body_q"][i], c["base_quat"][i])) for i in range(len(st))])
rob = la.resample(pt, st, rob, a.lag)

print(f"{'axis':6s} {'human mean(std) [min..max]':28s} {'robot mean(std) [min..max]':28s} {'MAE':>5s} {'corr':>5s} {'std ratio':>9s}")
for j, n in enumerate(["pitch", "roll", "twist"]):
    h, r = hum[:, j], rob[:, j]
    print(f"{n:6s} {h.mean():6.1f}({h.std():4.1f}) [{h.min():5.1f}..{h.max():5.1f}]   {r.mean():6.1f}({r.std():4.1f}) [{r.min():5.1f}..{r.max():5.1f}]   "
          f"{np.abs(h - r).mean():5.1f} {np.corrcoef(h, r)[0, 1]:5.2f} {r.std() / (h.std() + 1e-9):9.2f}")
limits = np.degrees([2.618, 0.52, 0.52])
m = (st >= pt[0] + a.lag) & (st <= pt[-1] + a.lag)
print("waist joints during the stream (deg), limits yaw/roll/pitch = +-%.0f/+-%.0f/+-%.0f:" % tuple(limits))
for j, n in enumerate(["waist_yaw", "waist_roll", "waist_pitch"]):
    w = np.degrees(c["body_q"][m, 12 + j])
    print(f"   {n:12s} min {w.min():6.1f}  max {w.max():6.1f}  near-limit {100 * (np.abs(np.abs(w) - limits[j]) < 3).mean():.1f}% of the time")
