#!/usr/bin/env bash
# usage: run_demo.sh <clip> <seconds> <fps>
# After GEM-X has produced outputs/<clip>/soma/<clip>/hpe_results.pt and the sim stack is up (pipeline/sim/start_stack.sh,
# band released): SMPL precompute -> paced replay with capture -> latency estimate -> the four videos, grid and strip.
# Set TRIAL=<name> to keep several runs of the same clip (default trial_1).
set -e
. "$(dirname "$0")/../lib/config.sh"
HERE="$(cd "$(dirname "$0")" && pwd)"
C=$1; SECS=$2; FPS=$3; O="$B/outputs/$C"; T="${TRIAL:-trial_1}"
[ -f "$O/soma/$C/hpe_results.pt" ] || { echo "no GEM-X result yet: run pipeline/gemx/run_gemx.sh $C" >&2; exit 1; }

echo "[A] precompute SMPL v3 frames"
( export PYTHONUNBUFFERED=1 CUDA_VISIBLE_DEVICES=$GPU_ID PYOPENGL_PLATFORM=egl EGL_PLATFORM=surfaceless; mkdir -p "$O/smpl"; cd "$R"
  "$PY_GEMX" "$HERE/replay/replay_paced.py" --gemx-root "$G" --sonic-root "$R" --pt "$O/soma/$C/hpe_results.pt" \
    --npz "$O/smpl/smpl_v3_frames.npz" --fps "$FPS" --precompute 2>&1 | grep "precompute\|Error\|Traceback" )

echo "[B] paced replay + capture"
bash "$HERE/replay/run_replay.sh" "$T" "$C" "$FPS" "$SECS" 2>&1 | tee "$LOGS/replay_${C}_$T.log"
grep -q "bad lines" "$LOGS/replay_${C}_$T.log" || { echo "replay did not complete" >&2; exit 1; }

echo "[C] latency estimate"
JSON=$("$PY_SIM" "$HERE/../analysis/estimate_lag.py" "$O/sonic/$T/capture.npz" | tail -n 1)
USE=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d['lag_s'] if d['mean_corr'] - d['corr_at_zero'] > 0.15 else 0.38)" "$JSON")
echo "estimate $JSON -> lag used for the sim videos: $USE s (0.38 s, measured on the dance clips, is the fallback when the curve is flat)"
echo "$USE" > "$O/sonic/$T/lag_used.txt"

echo "[D] videos"
bash "$HERE/video/make_videos.sh" "$C" "$T" "$SECS" "$USE" "$FPS"
echo "done: ${FINAL_DIR:-$O/videos/final}"
