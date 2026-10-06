#!/usr/bin/env bash
# usage: run_replay.sh <trial> <clip> <fps> <seconds> [win_w win_h]
# Needs the stack from pipeline/sim/start_stack.sh (control started, elastic band released, streaming off) and
# $SONIC_WORK/outputs/<clip>/smpl/smpl_v3_frames.npz. Turns on the deploy's ZMQ streaming, publishes the SMPL frames on a
# wall-clock schedule, plays the human clip next to the sim viewer, screen-records both, and captures the SMPL stream and
# the robot state to outputs/<clip>/sonic/<trial>/capture.npz. Streaming is switched off again at the end.
. "$(dirname "$0")/../../lib/config.sh"
T=$1; C=$2; FPS=$3; DUR=$4; WW=${5:-640}; WH=${6:-360}
HERE="$(cd "$(dirname "$0")" && pwd)"; S="$TMUX_SESSION"
VID="$B/data/clips/$C.mp4"; O="$B/outputs/$C"; mkdir -p "$O/videos" "$O/sonic/$T"
export DISPLAY=":$DISPLAY_NUM" XAUTHORITY="$B/tmp/xauth_vnc"
count() { local n; n=$(grep -c "$1" "$2" 2>/dev/null); echo "${n:-0}"; }

pgrep -u "$(id -un)" -f "^./target/release/g1_deploy_onnx_ref" >/dev/null || { echo "ABORT: deploy not running"; exit 1; }
grep -q "transitioning to CONTROL" "$LOGS/deploy.log" || { echo "ABORT: control not started"; exit 1; }
grep -a "STREAMING MODE" "$LOGS/deploy.log" | tail -n 1 | grep -q ENABLED && { echo "ABORT: streaming mode already enabled"; exit 1; }
F0=$(count fallen "$LOGS/sim.log"); D0=$(wc -l < "$LOGS/deploy.log")

tmux send-keys -t "$S:deploy" Enter; sleep 3
grep -a "ZMQ STREAMING MODE: ENABLED" "$LOGS/deploy.log" >/dev/null || { echo "ABORT: streaming mode not enabled"; exit 1; }
echo "streaming mode enabled"

ffmpeg -v error -y -f x11grab -framerate 30 -video_size 1280x640 -i ":$DISPLAY_NUM+0,0" -c:v libx264 -preset ultrafast -crf 20 -pix_fmt yuv420p "$O/videos/${T}_screen_raw.mp4" &
REC=$!
"$R/.venv_sim/bin/python" "$HERE/capture_streams.py" --out "$O/sonic/$T/capture.npz" --seconds 600 --pose-port "$ZMQ_POSE_PORT" --debug-port "$ZMQ_DEBUG_PORT" > "$O/sonic/$T/capture.log" 2>&1 &
CAP=$!
sleep 1
( export PYTHONUNBUFFERED=1 CUDA_VISIBLE_DEVICES=$GPU_ID; . "$B/venvs/gemx/bin/activate"; cd "$R"
  exec python "$HERE/replay_paced.py" --gemx-root "$G" --sonic-root "$R" --npz "$O/smpl/smpl_v3_frames.npz" --fps "$FPS" --port "$ZMQ_POSE_PORT" --start-delay 2 --publish ) > "$O/sonic/$T/publisher.log" 2>&1 &
PUB=$!
for _ in $(seq 1 200); do grep -aq "frame 1 sent" "$O/sonic/$T/publisher.log" && break; sleep 0.1; done
SDL_VIDEODRIVER=x11 SDL_AUDIODRIVER=dummy ffplay -v warning -an -autoexit -x "$WW" -y "$WH" -left 0 -top 0 -window_title human_clip -t "$DUR" "$VID" &
FP=$!
wait $PUB; echo "publisher finished"; sleep 3
tmux send-keys -t "$S:deploy" Enter; sleep 2
kill -INT $CAP 2>/dev/null; wait $CAP 2>/dev/null
kill -INT $REC 2>/dev/null; wait $REC 2>/dev/null; kill $FP 2>/dev/null

tail -n +$((D0+1)) "$LOGS/deploy.log" > "$O/sonic/$T/deploy.log"
{ grep "paced" "$O/sonic/$T/publisher.log"
  echo "falls during trial: $(( $(count fallen "$LOGS/sim.log") - F0 ))"
  echo "bad lines in deploy log: $(grep -v InferenceEngine.cpp "$O/sonic/$T/deploy.log" | grep -aciE 'nan|exception|segfault|fatal|failed|error')"
} | tee "$O/sonic/$T/summary.txt"
