# Sourced by every pipeline script: loads config.env and derives the common paths.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${SONIC_CONFIG:-$ROOT/config.env}"
if [ ! -f "$CONFIG_FILE" ]; then
  echo "missing $CONFIG_FILE: copy config.example.env to config.env and edit it" >&2; exit 1
fi
set -a; . "$CONFIG_FILE"; set +a
: "${SONIC_WORK:?set SONIC_WORK in config.env}"

B="$SONIC_WORK"                       # work dir
R="$B/repos/GR00T-WholeBodyControl"   # NVIDIA SONIC
G="$B/repos/GEM-X"                    # NVIDIA GEM-X
LOGS="$B/logs"
PY_GEMX="${PY_GEMX:-$B/venvs/gemx/bin/python}"      # GEM-X env (torch cu130, SOMA, detectron2)
PY_SIM="${PY_SIM:-$R/.venv_sim/bin/python}"            # SONIC sim env (mujoco, pinocchio, opencv)
PY_TOOLS="${PY_TOOLS:-$B/venvs/tools/bin/python}"      # small env with matplotlib + huggingface_hub
GPU_ID="${GPU_ID:-0}"
TMUX_SESSION="${TMUX_SESSION:-vnc}"
DISPLAY_NUM="${DISPLAY_NUM:-77}"
VNC_PORT="${VNC_PORT:-5977}"
NOVNC_PORT="${NOVNC_PORT:-6088}"
ZMQ_POSE_PORT="${ZMQ_POSE_PORT:-5556}"
ZMQ_DEBUG_PORT="${ZMQ_DEBUG_PORT:-5557}"
ENV_FILE="${ENV_FILE:-$B/.env}"
mkdir -p "$LOGS" "$B/tmp"

# Keep caches under the work dir so nothing lands in $HOME (handy on shared machines).
export UV_CACHE_DIR="${UV_CACHE_DIR:-$B/.uv-cache}" UV_PYTHON_INSTALL_DIR="${UV_PYTHON_INSTALL_DIR:-$B/.uv-python}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$B/.cache}" PIP_CACHE_DIR="${PIP_CACHE_DIR:-$B/.pip-cache}"
export TORCH_HOME="${TORCH_HOME:-$B/.torch}" HF_HOME="${HF_HOME:-$B/.hf-cache}" TMPDIR="${TMPDIR:-$B/tmp}"
export GIT_CONFIG_GLOBAL="${GIT_CONFIG_GLOBAL:-$B/tmp/gitconfig}"
[ -d "$B/tools/uv" ] && export PATH="$B/tools/uv:$B/tools/bin:$PATH"

load_hf_token() { [ -f "$ENV_FILE" ] && { set -a; . "$ENV_FILE"; set +a; }; }
