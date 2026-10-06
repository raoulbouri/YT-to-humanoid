"""Paced SOMA->SMPL v3 replay (glue code, NOT part of NVIDIA SONIC).

Why: NVIDIA's soma_pt_to_sonic_v3.py does `publish(convert(frame)); sleep(1/fps)`, so each frame costs
convert-time + 1/fps and the stream runs slower than real time (measured 14.3 fps instead of 23.976).
This script reuses NVIDIA's SomaToSmpl (converter) and SonicV3Publisher (packer/ZMQ) unchanged, but
  stage 1 (--precompute): converts every frame once and saves them to an .npz  (no timing involved)
  stage 2 (--publish):    sends the saved frames on an absolute wall-clock schedule t0 + i/fps.
"""
import argparse, os, sys, time
from pathlib import Path
import numpy as np
ap = argparse.ArgumentParser()
ap.add_argument("--gemx-root", required=True); ap.add_argument("--sonic-root", required=True)
ap.add_argument("--pt"); ap.add_argument("--npz", required=True, help="precomputed frames file (written by --precompute, read by --publish)")
ap.add_argument("--precompute", action="store_true"); ap.add_argument("--publish", action="store_true")
ap.add_argument("--fps", type=float, required=True); ap.add_argument("--max-frames", type=int, default=0)
ap.add_argument("--port", type=int, default=5556); ap.add_argument("--smooth", type=float, default=0.0)
ap.add_argument("--start-delay", type=float, default=2.0)
a = ap.parse_args()
sys.path.insert(0, a.gemx_root); sys.path.insert(0, a.sonic_root); sys.path.insert(0, str(Path(a.sonic_root) / "gear_sonic/examples/live_camera_teleop"))
import torch
if a.precompute:
    from gem.utils.soma_utils.soma_layer import SomaLayer
    from soma_to_smpl import SomaToSmpl
    g = torch.load(a.pt, weights_only=False)["body_params_global"]; T = g["body_pose"].shape[0]
    if a.max_frames: T = min(T, a.max_frames)
    soma = SomaLayer(data_root=str(Path(a.gemx_root) / "inputs" / "soma_assets"), low_lod=True, device="cuda", identity_model_type="mhr", mode="warp")
    conv = SomaToSmpl(soma, device="cuda", smooth=a.smooth, sonic_root=a.sonic_root)
    out = {k: [] for k in ("smpl_joints", "smpl_pose", "body_quat", "wrists")}
    t0 = time.time()
    for t in range(T):
        r = conv.convert({k: g[k][t] for k in ("body_pose", "global_orient", "identity_coeffs", "scale_params")})
        for k in out: out[k].append(np.asarray(r[k], dtype=np.float32).reshape(r[k].shape[1:]))
    np.savez(a.npz, fps=a.fps, **{k: np.stack(v) for k, v in out.items()})
    w = np.stack(out["wrists"]); sp = np.abs(np.stack(out["smpl_pose"])).max()
    print(f"[precompute] {T} frames in {time.time() - t0:.1f}s -> {a.npz}; wrists std {w.std(0).round(3)}, smpl_pose abs max {sp:.3f}", flush=True)
if a.publish:
    from soma_to_smpl import SonicV3Publisher
    d = np.load(a.npz); T = len(d["smpl_joints"]); T = min(T, a.max_frames) if a.max_frames else T
    pub = SonicV3Publisher(port=a.port, sonic_root=a.sonic_root)
    print(f"[paced] bound tcp://*:{a.port}; {T} frames at {a.fps} fps; start in {a.start_delay}s", flush=True)
    time.sleep(a.start_delay); t0 = time.perf_counter(); late = []
    for i in range(T):
        target = t0 + i / a.fps
        while True:
            now = time.perf_counter()
            if now >= target: break
            time.sleep(min(0.002, target - now))
        late.append(time.perf_counter() - target)
        pub.publish({k: d[k][i:i+1] for k in ("smpl_joints", "smpl_pose", "body_quat", "wrists")})
        if i == 0: print("[paced] frame 1 sent", flush=True)
    el = time.perf_counter() - t0; late = np.array(late) * 1000
    print(f"[paced] done: {T} frames in {el:.2f}s (nominal {T/a.fps:.2f}s); lateness ms mean {late.mean():.2f} max {late.max():.2f}", flush=True)
    time.sleep(0.5); pub.close()
