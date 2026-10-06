#!/usr/bin/env python
"""Plot the output of angle_compare.py. usage: plot_angles.py <out_prefix>   (writes <out_prefix>_angles.png; needs matplotlib)"""
import sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

p = sys.argv[1]; a = np.load(p + ".npz"); w = np.load(p + "_wrist.npz")
keys = list(a["keys"]); t = a["t"]; H = a["human"]; R = a["robot"]
fig, ax = plt.subplots(3, 3, figsize=(16, 10))
for ax_, k in zip(ax.ravel()[:6], ["l_elbow_flex", "r_elbow_flex", "l_shoulder_elev", "r_shoulder_elev", "l_hip_flex", "l_knee_flex"]):
    j = keys.index(k); ax_.plot(t, H[:, j], label="human (GEM-X -> SMPL)"); ax_.plot(t, R[:, j], label="robot (FK of measured joints)"); ax_.set_title(k + " (deg)")
for ax_, (s, side) in zip(ax.ravel()[6:8], [(0, "left"), (1, "right")]):
    ax_.plot(t, np.abs(w["human"][:, s, 1]), label="human"); ax_.plot(t, np.abs(w["robot"][:, s, 1]), label="robot"); ax_.set_title(side + " wrist lateral distance / arm length")
ax.ravel()[8].plot(t, w["human"][:, 0, 0], label="human L"); ax.ravel()[8].plot(t, w["robot"][:, 0, 0], label="robot L"); ax.ravel()[8].set_title("left wrist forward(+)/behind(-) / arm length")
ax.ravel()[0].legend()
for x in ax[2]: x.set_xlabel("time (s)")
plt.tight_layout(); plt.savefig(p + "_angles.png", dpi=70); print("wrote", p + "_angles.png")
