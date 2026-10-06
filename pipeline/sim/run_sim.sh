#!/usr/bin/env bash
# NVIDIA's MuJoCo sim with its viewer window, on the virtual display (software GL).
. "$(dirname "$0")/../../lib/config.sh"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$B/.config}" XDG_DATA_HOME="${XDG_DATA_HOME:-$B/.local-share}"
export DISPLAY=":$DISPLAY_NUM" XAUTHORITY="$B/tmp/xauth_vnc" LIBGL_ALWAYS_SOFTWARE=1
cd "$R" && . .venv_sim/bin/activate
python gear_sonic/scripts/run_sim_loop.py 2>&1 | tee "$LOGS/sim.log"
