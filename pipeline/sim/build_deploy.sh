#!/usr/bin/env bash
# Builds NVIDIA's C++ deploy (needs TensorRT, see docs/SETUP.md). NPROC_BUILD caps the cores used (shared machines).
. "$(dirname "$0")/deploy_env.sh"
if [ -n "${NPROC_BUILD:-}" ]; then CMD=(taskset -c "0-$((NPROC_BUILD-1))" just build); else CMD=(just build); fi
"${CMD[@]}" 2>&1 | tee "$LOGS/just_build.log"
echo "BUILD_EXIT=${PIPESTATUS[0]}" >> "$LOGS/just_build.log"
