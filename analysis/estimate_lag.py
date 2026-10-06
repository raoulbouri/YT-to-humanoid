#!/usr/bin/env python
"""Pipeline latency: the delay that maximises the mean correlation between human and robot limb angles (offset-invariant).
usage: estimate_lag.py <capture.npz> [--scene scene.xml]   (last stdout line is JSON)
Only meaningful for motions with enough movement: on slow clips the correlation curve is flat."""
import argparse, json, numpy as np
import limb_angles as la

ap = argparse.ArgumentParser(); ap.add_argument("capture"); ap.add_argument("--scene")
a = ap.parse_args()
c = np.load(a.capture); names, Ha, Ra = la.angle_table(c, la.RobotFK(a.scene))
pt, st = c["pose_t"], c["state_t"]
use = [j for j, k in enumerate(names) if k != "torso_lean"]
lags = np.arange(0, 1.01, 0.02); scores = []
for l in lags:
    Rm = la.resample(pt, st, Ra, l)
    scores.append(np.nanmean([np.corrcoef(Ha[:, j], Rm[:, j])[0, 1] for j in use]))
scores = np.array(scores); b = int(np.argmax(scores))
print("corr vs lag: " + " ".join(f"{l:.2f}s:{s:.3f}" for l, s in zip(lags[::10], scores[::10])))
print(json.dumps({"lag_s": round(float(lags[b]), 2), "mean_corr": round(float(scores[b]), 3), "corr_at_zero": round(float(scores[0]), 3)}))
