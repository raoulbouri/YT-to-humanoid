"""Checks for NVIDIA's SOMA -> SMPL converter with the local patch (patches/soma_to_smpl_public_names.patch).
usage: python tests/test_converter.py <hpe_results.pt>      (GEM-X env, needs the GPU; reads $SONIC_WORK)
Without the patch, T3/T4 fail: the converter indexes the 77-joint output with names from the 110-joint internal rig."""
import os, sys
import numpy as np
import torch

work = os.environ["SONIC_WORK"]
gemx = f"{work}/repos/GEM-X"; sonic = f"{work}/repos/GR00T-WholeBodyControl"
sys.path[:0] = [gemx, sonic, f"{sonic}/gear_sonic/examples/live_camera_teleop"]
from gem.utils.soma_utils.soma_layer import SomaLayer
from soma_to_smpl import SomaToSmpl


def ok(msg):
    print("PASS:", msg, flush=True)


soma = SomaLayer(data_root=f"{gemx}/inputs/soma_assets", low_lod=True, device="cuda", identity_model_type="mhr", mode="warp")
ok("T1 SOMA layer initialises")
g = torch.load(sys.argv[1], weights_only=False)["body_params_global"]
frame = {k: g[k][0] for k in ("body_pose", "global_orient", "identity_coeffs", "scale_params")}
t = lambda x: torch.as_tensor(x, dtype=torch.float32, device="cuda")[None]
out = soma(body_pose=t(frame["body_pose"]), global_orient=t(frame["global_orient"]), transl=torch.zeros(1, 3, device="cuda"),
           identity_coeffs=t(frame["identity_coeffs"]), scale_params=t(frame["scale_params"]))
assert tuple(out["joints"][0].shape) == (77, 3)
ok("T2 one frame gives joints (77, 3)")

conv = SomaToSmpl(soma, device="cuda", smooth=0.0, sonic_root=sonic)
names = conv.soma_joint_names
assert len(names) == 77, len(names)
ok("T3 converter name list has 77 entries (Root stripped)")
idx = list(conv.smpl_idx)
assert len(idx) == 24 and min(idx) >= 0 and max(idx) < 77, (min(idx), max(idx))
ok(f"T4 24 SMPL indices, all within 0..76 (max {max(idx)})")
assert names[0] == "Hips" and list(names) == list(soma.soma.public_joint_names[1:])
ok("T5 names equal SOMA's public_joint_names[1:], the order of the output joints")
print("mapping:", ", ".join(f"{i}:{names[i]}" for i in idx), flush=True)

res = conv.convert(frame)
torch.cuda.synchronize()
assert tuple(res["smpl_joints"].shape)[-2:] == (24, 3)
ok("T6 converter returns (24, 3) joints with no CUDA index error")
assert all(np.isfinite(np.asarray(v, dtype=np.float64)).all() for v in res.values())
ok("T7 all outputs finite")
j = np.asarray(res["smpl_joints"]).reshape(24, 3)
assert j[7][2] < j[0][2] and j[8][2] < j[0][2] and j[15][2] > j[0][2]
ok("T8 ankles below the pelvis, head above (z up)")
