#!/usr/bin/env bash
# usage: vnc_stack.sh xvfb|x11vnc|novnc     (run each in its own tmux window; start_stack.sh does that)
# Virtual display + VNC + noVNC, localhost only, X cookie + VNC password (generated on first use, stored outside the repo).
. "$(dirname "$0")/../../lib/config.sh"
XVFB_BIN="${XVFB_BIN:-$(command -v Xvfb)}"; X11VNC_BIN="${X11VNC_BIN:-$(command -v x11vnc)}"
WEBSOCKIFY_BIN="${WEBSOCKIFY_BIN:-$(command -v websockify)}"; NOVNC_DIR="${NOVNC_DIR:-/usr/share/novnc}"
XAUTH_BIN="${XAUTH_BIN:-$(command -v xauth)}"
export HOME="$B/tmp/home"; mkdir -p "$HOME"
[ -n "${VNC_LD_LIBRARY_PATH:-}" ] && export LD_LIBRARY_PATH="$VNC_LD_LIBRARY_PATH${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export XAUTHORITY="$B/tmp/xauth_vnc"
PASSFILE="$B/tmp/vncpass.txt"
case "$1" in
  xvfb)
    rm -f "$XAUTHORITY"
    "$XAUTH_BIN" -f "$XAUTHORITY" add ":$DISPLAY_NUM" . "$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')"; chmod 600 "$XAUTHORITY"
    exec "$XVFB_BIN" ":$DISPLAY_NUM" -screen 0 1280x800x24 -nolisten tcp +extension GLX +iglx -auth "$XAUTHORITY" -xkbdir /usr/share/X11/xkb ;;
  x11vnc)
    [ -f "$PASSFILE" ] || { head -c 24 /dev/urandom | base64 | tr -dc A-Za-z0-9 | head -c 10 > "$PASSFILE"; chmod 600 "$PASSFILE"; echo "VNC password written to $PASSFILE" >&2; }
    "$X11VNC_BIN" -storepasswd "$(cat "$PASSFILE")" "$B/tmp/vncpasswd" >/dev/null 2>&1; chmod 600 "$B/tmp/vncpasswd"
    exec "$X11VNC_BIN" -display ":$DISPLAY_NUM" -auth "$XAUTHORITY" -rfbauth "$B/tmp/vncpasswd" -localhost -forever -shared -rfbport "$VNC_PORT" ;;
  novnc)
    exec "$WEBSOCKIFY_BIN" --web "$NOVNC_DIR" "127.0.0.1:$NOVNC_PORT" "localhost:$VNC_PORT" ;;
  *) echo "usage: vnc_stack.sh xvfb|x11vnc|novnc" >&2; exit 2 ;;
esac
