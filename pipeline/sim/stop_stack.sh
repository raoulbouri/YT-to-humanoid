#!/usr/bin/env bash
# Stops the tmux session and any display / VNC / noVNC process of this stack that outlived it (Xvfb does).
. "$(dirname "$0")/../../lib/config.sh"
tmux kill-session -t "$TMUX_SESSION" 2>/dev/null && echo "stopped tmux session $TMUX_SESSION" || echo "no tmux session $TMUX_SESSION"
sleep 2
ME="$(id -un)"
# Patterns are anchored to the start of the process command line so a caller whose own command line merely mentions these
# names is not matched.
pkill -u "$ME" -f "^([^ ]*/)?Xvfb :$DISPLAY_NUM " 2>/dev/null
pkill -u "$ME" -f "^([^ ]*/)?x11vnc .*-rfbport $VNC_PORT" 2>/dev/null
pkill -u "$ME" -f "^[^ ]*python[^ ]* [^ ]*websockify .*127\.0\.0\.1:$NOVNC_PORT" 2>/dev/null
pkill -u "$ME" -f "^\./target/release/g1_deploy_onnx_ref" 2>/dev/null
pkill -u "$ME" -f "^python gear_sonic/scripts/run_sim_loop\.py" 2>/dev/null
sleep 1; rm -f "/tmp/.X11-unix/X$DISPLAY_NUM" "/tmp/.X$DISPLAY_NUM-lock"
echo "left running: $(pgrep -u "$ME" -f "^([^ ]*/)?Xvfb :$DISPLAY_NUM |^\./target/release/g1_deploy_onnx_ref|^python gear_sonic/scripts/run_sim_loop\.py" | wc -l) process(es)"
