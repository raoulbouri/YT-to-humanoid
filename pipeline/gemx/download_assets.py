"""Fetch the GEM-X files needed for demo_soma_onnx.py --no-imgfeat. usage: download_assets.py <GEM-X checkout>"""
import os, sys
from huggingface_hub import hf_hub_download

os.chdir(sys.argv[1])
REPO = "nvidia/GEM-X"
items = [("gem_soma.ckpt", "inputs/pretrained"), ("mhr_model.pt", "inputs/mhr_data"),
         ("scale_mean.pth", "inputs/soma_data"), ("scale_comps.pth", "inputs/soma_data")]
for name in ["vitpose", "gem_denoiser", "gem_denoiser_no_imgfeat"]:
    items += [(f"onnx/{name}.onnx", "inputs"), (f"onnx/{name}.onnx.data", "inputs")]
for fn, dst in items:
    try:
        p = hf_hub_download(repo_id=REPO, filename=fn, local_dir=dst)
        print("OK", fn, os.path.getsize(p), flush=True)
    except Exception as e:
        print("FAIL", fn, type(e).__name__, str(e)[:150], flush=True)
