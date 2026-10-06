#!/usr/bin/env python
"""Human (SMPL stream) vs robot (FK of measured joints): limb angles and wrist positions.
usage: angle_compare.py <capture.npz> <out_prefix> [--scene scene.xml]
Writes <out_prefix>.json/.npz and <out_prefix>_wrist.npz (input for plot_angles.py)."""
import argparse, json, numpy as np
import limb_angles as la

ap = argparse.ArgumentParser(); ap.add_argument("capture"); ap.add_argument("out"); ap.add_argument("--scene")
a = ap.parse_args()
c = np.load(a.capture); fk = la.RobotFK(a.scene)
names, Ha, Ra = la.angle_table(c, fk)
pt, st = c["pose_t"], c["state_t"]

lags = np.arange(0, 1.01, 0.02)
mae = [np.abs(la.resample(pt, st, Ra, l) - Ha).mean() for l in lags]
best = float(lags[int(np.argmin(mae))]); Rm = la.resample(pt, st, Ra, best); half = len(pt) // 2
res = {"best_lag_s": best, "mean_abs_err_deg_all": float(np.abs(Rm - Ha).mean()),
       "mae_vs_lag": {f"{l:.2f}": round(float(v), 2) for l, v in zip(lags[::5], mae[::5])}, "per_angle": {}}
for j, k in enumerate(names):
    h, r = Ha[:, j], Rm[:, j]
    res["per_angle"][k] = {"human_mean": round(float(h.mean()), 1), "robot_mean": round(float(r.mean()), 1),
                           "bias_robot_minus_human": round(float((r - h).mean()), 1), "human_std": round(float(h.std()), 1),
                           "robot_std": round(float(r.std()), 1), "mae": round(float(np.abs(r - h).mean()), 1),
                           "corr": round(float(np.corrcoef(h, r)[0, 1]), 2),
                           "mae_first_half": round(float(np.abs(r - h)[:half].mean()), 1),
                           "mae_second_half": round(float(np.abs(r - h)[half:].mean()), 1)}
json.dump(res, open(a.out + ".json", "w"), indent=1)
np.savez(a.out + ".npz", keys=names, t=pt - pt[0], human=Ha, robot=Rm, lag=best)

print(f"lag with the lowest mean error: {best:.2f} s (the error curve is often flat; use estimate_lag.py for the latency) | overall MAE {res['mean_abs_err_deg_all']:.1f} deg")
print(f"{'angle':18s} {'human':>6s} {'robot':>6s} {'bias':>6s} {'MAE':>5s} {'corr':>5s}")
for k, v in res["per_angle"].items():
    print(f"{k:18s} {v['human_mean']:6.1f} {v['robot_mean']:6.1f} {v['bias_robot_minus_human']:6.1f} {v['mae']:5.1f} {v['corr']:5.2f}")

Hp = np.array([[la.hand_positions(la.human_keypoints(c["smpl_joints"][i]))[s] for s in "lr"] for i in range(len(pt))])
Rp = np.array([[la.hand_positions(fk.keypoints(c["body_q"][i], c["base_quat"][i]))[s] for s in "lr"] for i in range(len(st))])
Rp = np.stack([la.resample(pt, st, Rp[:, s], best) for s in range(2)], 1)
print("wrist position in the pelvis-yaw frame / arm length, human vs robot:")
for s, side in enumerate(["left", "right"]):
    for ax, an in enumerate(["forward", "lateral", "up"]):
        h, r = Hp[:, s, ax], Rp[:, s, ax]
        print(f"  {side:5s} wrist {an:8s} human {h.mean():+.2f} [{h.min():+.2f}..{h.max():+.2f}]  robot {r.mean():+.2f} [{r.min():+.2f}..{r.max():+.2f}]  MAE {np.abs(h - r).mean():.2f}  corr {np.corrcoef(h, r)[0, 1]:.2f}")
np.savez(a.out + "_wrist.npz", human=Hp, robot=Rp, t=pt - pt[0])
