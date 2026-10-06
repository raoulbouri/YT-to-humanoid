#!/usr/bin/env bash
# usage: run_deploy.sh [deploy.sh args]      e.g.  run_deploy.sh --input-type zmq sim
# NVIDIA's own deploy.sh; waits for keys: Enter (confirm), ']' (start control), Enter (toggle ZMQ streaming).
. "$(dirname "$0")/deploy_env.sh"
[ -n "${CLANG_DIR:-}" ] && export PATH="$PATH:$CLANG_DIR"     # deploy.sh checks for clang; appended so it never shadows gcc
export CUDA_VISIBLE_DEVICES=$GPU_ID
bash deploy.sh "$@" 2>&1 | tee "$LOGS/deploy.log"
