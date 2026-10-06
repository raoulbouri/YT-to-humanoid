#!/usr/bin/env bash
# usage: run_gemx.sh <clip>     (reads $SONIC_WORK/data/clips/<clip>.mp4)
# Runs NVIDIA's offline GEM-X demo (static camera, 2D-keypoint-only) and writes
# $SONIC_WORK/outputs/<clip>/soma/<clip>/hpe_results.pt. CPU ONNX build: ~1 s of video per ~1 min.
. "$(dirname "$0")/../../lib/config.sh"
N=$1
load_hf_token
export CUDA_VISIBLE_DEVICES=$GPU_ID PYOPENGL_PLATFORM=egl EGL_PLATFORM=surfaceless PYTHONUNBUFFERED=1
cd "$G" && . "$B/venvs/gemx/bin/activate"
mkdir -p "$B/outputs/$N/soma"
python scripts/demo/demo_soma_onnx.py --video "$B/data/clips/$N.mp4" --output_root "$B/outputs/$N/soma" -s --no-imgfeat 2>&1 | tee "$LOGS/gemx_$N.log"
echo "GEMX_EXIT=${PIPESTATUS[0]}" >> "$LOGS/gemx_$N.log"
