#!/usr/bin/env bash
# Downloads the GEM-X weights and ONNX models used by the --no-imgfeat path into the GEM-X checkout, and links the SOMA assets.
set -e
. "$(dirname "$0")/../../lib/config.sh"
load_hf_token
export HF_HUB_DISABLE_TELEMETRY=1
mkdir -p "$G/inputs"
ln -sfn "$G/third_party/soma/assets" "$G/inputs/soma_assets"
"$B/venvs/gemx/bin/python" "$(dirname "$0")/download_assets.py" "$G"
