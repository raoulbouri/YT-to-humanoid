"""Human SMPL skeleton (the 24 joints streamed to SONIC) as 960x540 frames: front and side views in a pelvis-yaw frame."""
import sys, os, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
npz, outdir = sys.argv[1], sys.argv[2]; os.makedirs(outdir, exist_ok=True)
J = np.load(npz)["smpl_joints"]; J = J.reshape(len(J), 24, 3)
def frame(j):
    P = j - j[0]; y = j[1] - j[2]; y = np.array([y[0], y[1], 0.0]); y /= np.linalg.norm(y) + 1e-9; z = np.array([0, 0, 1.0]); x = np.cross(y, z)
    return np.stack([P @ x, P @ y, P @ z], 1)
H = np.array([frame(j) for j in J])
parents = [-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19, 20, 21]
left = {1, 4, 7, 10, 13, 16, 18, 20, 22}; right = {2, 5, 8, 11, 14, 17, 19, 21, 23}
col = lambda i: "tab:blue" if i in left else ("tab:red" if i in right else "#333")
fig, axs = plt.subplots(1, 2, figsize=(9.6, 5.4), dpi=100); fig.patch.set_facecolor("#f4f4f4")
fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01, wspace=0.02)
arts = []
for ax, (title, ax_i) in zip(axs, [("front view", 1), ("side view (faces right)", 0)]):
    ax.set_xlim(-0.75, 0.75); ax.set_ylim(-1.3, 0.85); ax.set_aspect("equal"); ax.axis("off"); ax.text(0, -1.2, title, ha="center", va="center", fontsize=11)
    ax.plot([-0.75, 0.75], [-1.0, -1.0], c="#bbb", lw=1)
    arts.append((ax_i, [ax.plot([], [], c=col(i), lw=3.5, solid_capstyle="round")[0] for i in range(1, 24)], ax.plot([], [], "o", c="#222", ms=3)[0]))
for k in range(len(H)):
    P = H[k]
    for ax_i, lines, dots in arts:
        for i, l in zip(range(1, 24), lines):
            p, q = P[i], P[parents[i]]; l.set_data([p[ax_i], q[ax_i]], [p[2], q[2]])
        dots.set_data(P[:, ax_i], P[:, 2])
    fig.savefig(f"{outdir}/f_{k:04d}.png", facecolor=fig.get_facecolor())
print("rendered", len(H))
