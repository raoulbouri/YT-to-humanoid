#!/usr/bin/env bash
# usage: make_videos.sh <clip> <trial> <seconds> <lag_s> [fps]
# Builds the demo videos from a finished replay: outputs/<clip>/videos/final/
#   original.mp4, skeleton.mp4, front.mp4, side.mp4   (960x540 each)
#   demo_grid_2x2.mp4 (1920x1080), demo_strip_1x4.mp4 (3840x540)
# The two sim views are re-rendered in MuJoCo from the logged robot state (not screen recordings) and shifted by <lag_s>
# (the measured pipeline latency, see analysis/estimate_lag.py) so they line up with the input.
set -e
. "$(dirname "$0")/../../lib/config.sh"
C=$1; T=$2; SECS=$3; LAG=$4; FPS=${5:-30}
HERE="$(cd "$(dirname "$0")" && pwd)"
O="$B/outputs/$C"; F="${FINAL_DIR:-$O/videos/final}"; W="$B/tmp/videos_${C}_$T"
rm -rf "$W"; mkdir -p "$F" "$W"; export MPLCONFIGDIR="$B/tmp/mpl"
FIT="scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2:black"
ENC=(-c:v libx264 -crf 18 -pix_fmt yuv420p)

echo "[1/5] original";  ffmpeg -v error -y -t "$SECS" -i "$B/data/clips/$C.mp4" -an -vf "$FIT,fps=$FPS" "${ENC[@]}" "$F/original.mp4"
echo "[2/5] skeleton";  "$PY_TOOLS" "$HERE/render_skeleton_tile.py" "$O/smpl/smpl_v3_frames.npz" "$W/skel" | tail -n 1
ffmpeg -v error -y -framerate "$FPS" -i "$W/skel/f_%04d.png" -t "$SECS" "${ENC[@]}" "$F/skeleton.mp4"
echo "[3/5] sim front + side (lag shift $LAG s)"
MUJOCO_GL=egl PYOPENGL_PLATFORM=egl MUJOCO_EGL_DEVICE_ID=$GPU_ID "$PY_SIM" "$HERE/render_sim_views.py" \
  --capture "$O/sonic/$T/capture.npz" --out-prefix "$W/sim" --seconds "$SECS" --lag "$LAG" --fps "$FPS" 2>&1 | grep -v EGLError | tail -n 2
mv "$W/sim_front.mp4" "$F/front.mp4"; mv "$W/sim_side.mp4" "$F/side.mp4"

echo "[4/5] labels"
"$PY_TOOLS" - "$W" <<'PY'
import sys, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
W = sys.argv[1]
def labels(path, size, items, fs, pad, y):
    fig = plt.figure(figsize=size, dpi=100); fig.patch.set_alpha(0)
    for x, yy, s in items:
        fig.text(x, yy, s, color="white", fontsize=fs, va="top", ha="left", bbox=dict(facecolor="black", alpha=0.55, pad=pad, edgecolor="none"))
    fig.savefig(path, transparent=True)
names = ["1  original video", "2  SMPL skeleton (input to SONIC)", "3  G1 simulation - front view", "4  G1 simulation - side view"]
labels(W + "/labels_grid.png", (19.2, 10.8), [(0.01, 0.985, names[0]), (0.51, 0.985, names[1]), (0.01, 0.485, names[2]), (0.51, 0.485, names[3])], 15, 5, 0)
labels(W + "/labels_strip.png", (38.4, 5.4), [(0.002 + 0.25 * i, 0.98, n) for i, n in enumerate(names)], 22, 6, 0)
PY
echo "[5/5] composite"
ffmpeg -v error -y -i "$F/original.mp4" -i "$F/skeleton.mp4" -i "$F/front.mp4" -i "$F/side.mp4" -i "$W/labels_grid.png" \
  -filter_complex "[0][1]hstack[a];[2][3]hstack[b];[a][b]vstack[g];[g][4]overlay=0:0[v]" -map "[v]" -r "$FPS" "${ENC[@]}" "$F/demo_grid_2x2.mp4"
ffmpeg -v error -y -i "$F/original.mp4" -i "$F/skeleton.mp4" -i "$F/front.mp4" -i "$F/side.mp4" -i "$W/labels_strip.png" \
  -filter_complex "[0][1][2][3]hstack=inputs=4[g];[g][4]overlay=0:0[v]" -map "[v]" -r "$FPS" "${ENC[@]}" "$F/demo_strip_1x4.mp4"
for f in original skeleton front side demo_grid_2x2 demo_strip_1x4; do
  echo -n "$f: "; ffprobe -v error -select_streams v:0 -show_entries stream=width,height,nb_frames -show_entries format=duration -of csv=p=0 "$F/$f.mp4" | tr '\n' ' '; echo
done
