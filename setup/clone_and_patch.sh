#!/usr/bin/env bash
# Clones NVIDIA's SONIC and GEM-X (and SOMA-X) into $SONIC_WORK/repos at the commits used here, applies the one local patch,
# and pulls the Git LFS files the pipeline needs. Re-runnable.
# Env: NVLABS_BASE (default https://github.com/NVlabs)   SKIP_LFS=1 to skip the LFS pulls
set -e
. "$(dirname "$0")/../lib/config.sh"
BASE="${NVLABS_BASE:-https://github.com/NVlabs}"
SONIC_COMMIT=b042411fae38ee4d1af9aac82a37a1f8d14d6dd0   # GR00T-WholeBodyControl, 2026-09-23
GEMX_COMMIT=32992550dba114c62243fb55e361311972dce8f9    # GEM-X, 2026-04-27
# SOMA-X: what the results were produced with. GEM-X itself records e0f8ff0ecfa3edbbb6058b1e0f08822ee2f84ee5 (March 2026);
# v0.3.3 is 18 commits newer. The converter patch is needed with v0.3.3; see docs/REPORT.md, deviation 13.
SOMA_COMMIT=d6aa640f7787498009c4e3d57fcc14a243905d10
mkdir -p "$B/repos"; cd "$B/repos"

# LFS smudge is skipped on clone: a full LFS checkout is many GB; only the needed paths are pulled below
[ -d GR00T-WholeBodyControl ] || GIT_LFS_SKIP_SMUDGE=1 git clone "$BASE/GR00T-WholeBodyControl.git"
GIT_LFS_SKIP_SMUDGE=1 git -C GR00T-WholeBodyControl checkout -q "$SONIC_COMMIT"

# no --recursive: GEM-X's soma-retargeter submodule uses an SSH URL, and we do not use it
[ -d GEM-X ] || GIT_LFS_SKIP_SMUDGE=1 git clone "$BASE/GEM-X.git"
GIT_LFS_SKIP_SMUDGE=1 git -C GEM-X checkout -q "$GEMX_COMMIT"
if [ ! -e GEM-X/third_party/soma/.git ]; then
  rmdir GEM-X/third_party/soma 2>/dev/null || true
  GIT_LFS_SKIP_SMUDGE=1 git clone "$BASE/SOMA-X.git" GEM-X/third_party/soma
fi
GIT_LFS_SKIP_SMUDGE=1 git -C GEM-X/third_party/soma checkout -q "$SOMA_COMMIT"

cd GR00T-WholeBodyControl
if git apply --check "$ROOT/patches/soma_to_smpl_public_names.patch" 2>/dev/null; then
  git apply "$ROOT/patches/soma_to_smpl_public_names.patch"; echo "applied soma_to_smpl_public_names.patch"
else
  git apply --check -R "$ROOT/patches/soma_to_smpl_public_names.patch" && echo "patch already applied"
fi

if [ -z "${SKIP_LFS:-}" ]; then
  git lfs pull -I "gear_sonic_deploy/reference/**,gear_sonic_deploy/g1/**,gear_sonic_deploy/thirdparty/**,gear_sonic/data/assets/robot_description/**,gear_sonic/data/robot_model/model_data/g1/**"
  git -C ../GEM-X/third_party/soma lfs pull -X "assets/images/**"
fi
echo "repos ready in $B/repos"
