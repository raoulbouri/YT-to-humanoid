# Setup

Built and tested on Ubuntu 24.04 (x86_64), one RTX 5090 (driver 580, CUDA toolkit 13.0). Versions and commits are in
[REPORT.md](REPORT.md). Everything installs without root except where noted. Heavy files (repos, venvs, TensorRT, clips,
outputs) live in `$SONIC_WORK`, never in this repo.

## Prerequisites
- `git`, `git-lfs`, `ffmpeg`, `tmux`, `cmake` + `gcc`, [`just`](https://just.systems), [`uv`](https://docs.astral.sh/uv/)
- CUDA toolkit with `nvcc` (needed to compile detectron2)
- **TensorRT 10.13.3.9 for CUDA 13.0** (tar package; NVIDIA developer login). SONIC's docs insist on exactly 10.13.
  Extract it to `$SONIC_WORK/TensorRT`.
- For the interactive sim view: `Xvfb`, `x11vnc`, `noVNC` + `websockify`, `xauth`, `xdotool`
  (`apt install xvfb x11vnc novnc websockify xauth xdotool`). Without root I used `apt-get download` + `dpkg -x` into a
  prefix and pointed `XVFB_BIN`, `X11VNC_BIN`, `NOVNC_DIR`, `VNC_LD_LIBRARY_PATH` at it (see `config.example.env`).

## Steps
```bash
cp config.example.env config.env        # set SONIC_WORK, adjust the optional tool paths
source lib/config.sh                     # gives you $B (work dir), $R (SONIC), $G (GEM-X) for the commands below

bash setup/clone_and_patch.sh            # NVIDIA repos at the commits used here + the converter patch
```

**GEM-X environment** (torch cu130: the RTX 5090 needs CUDA >= 12.8 wheels; GEM-X's README says cu126)
```bash
uv venv $B/venvs/gemx --python 3.12 && source $B/venvs/gemx/bin/activate
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
uv pip install -e $G/third_party/soma
uv pip install -e $G
uv pip install cloudpickle fvcore iopath pycocotools braceexpand roma 'setuptools<75' pyzmq scipy
CUDA_HOME=/usr/local/cuda-13.0 TORCH_CUDA_ARCH_LIST=12.0 MAX_JOBS=8 \
  uv pip install 'git+https://github.com/facebookresearch/detectron2.git@a1ce2f9' --no-build-isolation --no-deps
python -c "import torch; print(torch.__version__, torch.version.cuda)"   # expect +cu130 / 13.0
```
Pitfall: in my run, resolving `setuptools<75` made uv swap in a mismatched PyPI torch. If the check above does not say
`+cu130`, reinstall `torch torchvision` from the cu130 index. The plain `onnxruntime` wheel is CPU-only, so GEM-X runs on CPU
here (about 1 minute per second of video).

**SONIC sim environment** (creates `$R/.venv_sim`)
```bash
cd $R && bash install_scripts/install_mujoco_sim.sh
```

**Small tools environment** (plots, labels)
```bash
uv venv $B/venvs/tools && uv pip install --python $B/venvs/tools/bin/python matplotlib numpy huggingface_hub
```

**Models**
```bash
cd $R && python download_from_hf.py            # SONIC default checkpoint (public, no token needed)
bash pipeline/gemx/download_assets.sh          # GEM-X weights + ONNX models (public); token optional via ENV_FILE
```

**Deploy build** (C++, needs TensorRT; `deploy.sh` also wants `clang` on PATH, set `CLANG_DIR` if it is not installed)
```bash
bash pipeline/sim/build_deploy.sh
```

**Check the converter**
```bash
$B/venvs/gemx/bin/python tests/test_converter.py $B/outputs/<clip>/soma/<clip>/hpe_results.pt
```

## Run a video
```bash
bash pipeline/data/download_clip.sh <youtube-url> <name>                       # optional
bash pipeline/data/prepare_clip.sh $B/data/raw/<name>.mp4 <clip> <start> <seconds> 30
bash pipeline/gemx/run_gemx.sh <clip>                                          # slow: CPU
bash pipeline/sim/start_stack.sh && bash pipeline/sim/release_band.sh          # sim + deploy, then release the elastic band
bash pipeline/run_demo.sh <clip> <seconds> 30                                  # SMPL, replay, capture, latency, videos
bash pipeline/video/make_gif.sh $B/outputs/<clip>/videos/final/demo_grid_2x2.mp4 assets/demo.gif
bash pipeline/sim/stop_stack.sh
```
To watch the sim live: `ssh -L 6088:localhost:6088 <host>` and open `http://localhost:6088/vnc.html?autoconnect=1&resize=scale`
(password in `$SONIC_WORK/tmp/vncpass.txt`).

## Notes
- The SONIC sim only releases its elastic band from a key press (`9`) in the MuJoCo viewer window. `release_band.sh` sends
  that key with `xdotool`; `ENABLE_ELASTIC_BAND: False` in the config crashes the sim (upstream bug).
- `deploy.sh` runs `install_deps.sh` (sudo apt) when it cannot find `just` or `clang`. Install those first or use `CLANG_DIR`.
