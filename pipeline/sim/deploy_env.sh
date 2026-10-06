# Sourced by build_deploy.sh / run_deploy.sh: build environment for NVIDIA's C++ deploy, then cd into it.
. "$(dirname "${BASH_SOURCE[0]}")/../../lib/config.sh"
export TensorRT_ROOT="${TENSORRT_ROOT:-$B/TensorRT}"        # TensorRT 10.13 (x86_64, CUDA 13.0 tarball)
export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}" CUDAToolkit_ROOT="${CUDA_HOME:-/usr/local/cuda}"
if [ -n "${DEPS_PREFIX:-}" ]; then                           # user-level msgpack / nlohmann-json / onnxruntime
  export onnxruntime_ROOT="$DEPS_PREFIX/onnxruntime"
  export CPATH="$DEPS_PREFIX/include:$DEPS_PREFIX/onnxruntime/include${CPATH:+:$CPATH}"
  export CMAKE_PREFIX_PATH="$DEPS_PREFIX:$DEPS_PREFIX/onnxruntime${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}"
  export LD_LIBRARY_PATH="$DEPS_PREFIX/onnxruntime/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
cd "$R/gear_sonic_deploy"
source scripts/setup_env.sh
