#!/usr/bin/env bash
# Starts display, VNC, noVNC, the sim and the deploy in one tmux session, confirms the deploy prompt and starts control.
# Afterwards release the elastic band (release_band.sh, or press 9 in the MuJoCo window over VNC).
# Stops at the first failure and says which step failed.
. "$(dirname "$0")/../../lib/config.sh"
HERE="$(cd "$(dirname "$0")" && pwd)"; S="$TMUX_SESSION"
fail() { echo "FAILED: $1" >&2; exit 1; }
alive() { tmux has-session -t "$S" 2>/dev/null || fail "tmux session '$S' ended after step '$1' (see its log or run that script by hand)"; }
wait_for() { for _ in $(seq 1 "$3"); do grep -aq "$1" "$2" 2>/dev/null && return 0; sleep 2; done; fail "timed out waiting for '$1' in $2"; }

tmux has-session -t "$S" 2>/dev/null && fail "tmux session '$S' already exists; run stop_stack.sh first"
[ -e "/tmp/.X11-unix/X$DISPLAY_NUM" ] && fail "display :$DISPLAY_NUM is already in use; run stop_stack.sh or change DISPLAY_NUM"
rm -f "$LOGS/deploy.log" "$LOGS/sim.log"
tmux new-session -d -s "$S" -n xvfb   "bash $HERE/vnc_stack.sh xvfb";   sleep 5; alive xvfb
tmux new-window  -t "$S"    -n x11vnc "bash $HERE/vnc_stack.sh x11vnc"; sleep 4; alive x11vnc
tmux new-window  -t "$S"    -n novnc  "bash $HERE/vnc_stack.sh novnc";  sleep 3; alive novnc
tmux new-window  -t "$S"    -n sim    "bash $HERE/run_sim.sh";          sleep 35; alive sim
tmux new-window  -t "$S"    -n deploy "bash $HERE/run_deploy.sh --input-type zmq sim"
wait_for "Proceed with deployment" "$LOGS/deploy.log" 90; tmux send-keys -t "$S:deploy" Enter
wait_for "Init Done" "$LOGS/deploy.log" 150                                   # first run builds the TensorRT engines (slow)
tmux send-keys -t "$S:deploy" "]"
wait_for "transitioning to CONTROL" "$LOGS/deploy.log" 15
echo "stack is up (control started). Viewer: ssh -L $NOVNC_PORT:localhost:$NOVNC_PORT <host>, then http://localhost:$NOVNC_PORT/vnc.html?autoconnect=1&resize=scale"
echo "VNC password: $B/tmp/vncpass.txt"
