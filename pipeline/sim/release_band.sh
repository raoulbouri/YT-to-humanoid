#!/usr/bin/env bash
# Sends the '9' key to the MuJoCo viewer window on the virtual display (toggles the sim's elastic band; run once).
# Needs xdotool (XDOTOOL_BIN or on PATH). Alternative: press 9 in the MuJoCo window over noVNC.
. "$(dirname "$0")/../../lib/config.sh"
XDOTOOL_BIN="${XDOTOOL_BIN:-$(command -v xdotool)}"
[ -x "$XDOTOOL_BIN" ] || { echo "xdotool not found; press 9 in the viewer instead" >&2; exit 1; }
DISPLAY=":$DISPLAY_NUM" XAUTHORITY="$B/tmp/xauth_vnc" "$XDOTOOL_BIN" key 9 && echo "sent key 9 (elastic band toggled)"
