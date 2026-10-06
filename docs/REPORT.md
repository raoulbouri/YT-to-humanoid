# Report: video -> GEM-X -> SMPL -> SONIC -> Unitree G1 (MuJoCo)

Detailed notes behind the README: what was built, how, what it produced, and what is still imperfect.
Everything ran on a remote GPU machine under `$SONIC_WORK` (called `$B` below). Read sections 7 and 8 before reusing any result.

Script names in this report refer to the repo layout (`pipeline/`, `analysis/`). A few early artefacts mentioned below
(the human | skeleton + robot-overlay video, an MJPEG viewer, the unpaced replay script, two camera edits to NVIDIA's G1 XML
files) were experiments that are not carried into this repo; the numbers all come from `analysis/` and `pipeline/`.

---

## 0. TL;DR

- A working, reproducible pipeline exists: a monocular video is run through NVIDIA GEM-X (SOMA body model), converted to SMPL joints by NVIDIA's `soma_to_smpl.py` (with one 5-line patch), streamed over ZMQ (protocol v3) to NVIDIA's released SONIC controller (TensorRT 10.13), which drives a simulated Unitree G1 in MuJoCo. Playback is visible live in a browser and recorded to video.
- Three videos were run end to end: a yoga clip (`clip_001`, side-on camera), a dance video (`dance_001`, frontal camera) and a CGI-character clip (`demo_001`, frontal, section 12).
- The robot never fell in any replay trial (0 "Robot has fallen" events in all 7 replay trials).
- Tracking quality is real but imperfect: human-vs-robot limb angles correlate strongly (0.8–0.97 on most limbs) with systematic offsets (arms ~20° more raised on the robot; hips/torso less flexed on the dance).
- The biggest quality issue found is not the controller but perception on side-on footage: GEM-X cannot see left-right arm spread from a profile camera (prayer hands came out 0.6 m apart).
- Not done: the ground-truth test (stream NVIDIA's own paired SMPL/robot sample data), three repeated trials of the dance and demo clips, and removal of a few local deviations from NVIDIA's code (section 8).

---

## 1. What was built (architecture)

```
 video (.mp4)
   │  (cut / constant-frame-rate prep: ffmpeg)
   ▼
 GEM-X  scripts/demo/demo_soma_onnx.py  -s --no-imgfeat        [CPU, ONNX Runtime]
   YOLOX + ByteTrack  →  ViTPose (77 2D keypoints)  →  GEM denoiser  →  SOMA body params
   │  hpe_results.pt  (body_pose 76x3, global_orient, identity_coeffs, scale_params, ...)
   ▼
 SOMA → SMPL  (NVIDIA soma_to_smpl.py, 24 SMPL joints, root-local, z-up)   [GPU 0, small]
   │  precomputed once  →  smpl_v3_frames.npz
   ▼
 replay_paced.py (mine)  publishes frames on an exact wall-clock schedule, ZMQ PUB :5556, protocol v3
   │  fields: smpl_joints[1,24,3]  smpl_pose[1,21,3]=0  joint_pos[1,29] (wrists)=0  joint_vel=0  body_quat  frame_index
   ▼
 SONIC deploy  g1_deploy_onnx_ref  (C++, TensorRT 10.13, --input-type zmq)         [GPU 0]
   SMPL encoder + decoder (ONNX → TRT engines)  →  29 joint targets at 50 Hz
   │  Unitree SDK2 / DDS on loopback
   ▼
 MuJoCo sim  gear_sonic/scripts/run_sim_loop.py   (G1 29-DoF + hands, scene_43dof.xml)  [CPU]
   viewed through a virtual display (Xvfb) → x11vnc → noVNC → your browser (ssh -L 6088)
   recorded by ffmpeg x11grab; robot joints + SMPL stream also captured to .npz for analysis
```

Key design facts of NVIDIA's pipeline (from reading the code, not assumptions):
- SONIC does the human→robot mapping inside the policy (the `smpl` encoder). There is no per-frame retargeting.
- Only `smpl_joints` and `body_quat` carry motion. `smpl_pose` and the wrist `joint_pos` fields are streamed as zeros by design, so wrists/hands are not tracked.
- No root translation is commanded; the robot tracks body pose and heading only.
- The sim's elastic band holds the robot up until released with key `9` in the MuJoCo viewer window.

---

## 2. Where everything lives

In this repo: code only (`pipeline/`, `analysis/`, `tests/`, `setup/`, `patches/`, `docs/`).
In `$SONIC_WORK` (not in git): `repos/` (NVIDIA's SONIC and GEM-X at pinned commits), `venvs/`, `TensorRT/`, `tools/`,
`data/{raw,clips}`, `outputs/<clip>/{soma,smpl,sonic,videos,analysis}`, `logs/`, `tmp/`.

Per clip, e.g. `outputs/demo_001/`:
- `soma/<clip>/`: GEM-X outputs, including `hpe_results.pt` (the SOMA pose) and overlay/mesh videos
- `smpl/smpl_v3_frames.npz`: the exact SMPL frames that were streamed
- `sonic/<trial>/`: `publisher.log`, `deploy.log` (slice for the trial), `capture.npz` (SMPL stream + robot joints on one clock), `summary.txt`, `lag_used.txt`
- `videos/final/`: the four 960x540 videos, the 2x2 grid and the 4-across strip

---

## 3. Environment record

| Item | Value |
|---|---|
| Machine | Ubuntu 24.04.3, x86_64, 32 cores, 2× RTX 5090 (sm_120), driver 580.173.02. Shared with other users; only GPU 0 used by me |
| System CUDA toolkit | 13.0.2 at `/usr/local/cuda-13.0` (read-only use; never modified) |
| TensorRT | 10.13.3.9 (`TensorRT-10.13.3.9.Linux.x86_64-gnu.cuda-13.0.tar`, sha256 `897261be948962c9eb5d3595625f91d85a9aa8b57601aed6efac3fd6d9ff6f53`) |
| GEAR-SONIC repo | `GR00T-WholeBodyControl` commit `b042411fae38ee4d1af9aac82a37a1f8d14d6dd0` (2026-09-23) |
| SONIC checkpoint | default release: `model_encoder.onnx` (sha256 `013ab028…`), `model_decoder.onnx` (`c7241a12…`), `planner_sonic.onnx` (`39b553e1…`) from HF `nvidia/GEAR-SONIC` (public, ungated) |
| GEM-X | commit `32992550dba114c62243fb55e361311972dce8f9`; weights from HF `nvidia/GEM-X` (`gem_soma.ckpt`, `mhr_model.pt`, scale data, ONNX: `vitpose`, `gem_denoiser`, `gem_denoiser_no_imgfeat`) |
| SOMA | SOMA-X v0.3.3, commit `d6aa640f7787498009c4e3d57fcc14a243905d10` (2026-09-29). **This is NOT GEM-X's recorded pin**: GEM-X pins `e0f8ff0ecfa3edbbb6058b1e0f08822ee2f84ee5` (the public mirror's initial commit, 2026-03-16); v0.3.3 is 18 commits newer (corrected 2026-10-05; an earlier version of this report wrongly said it was the pin) |
| Others | soma-retargeter `cbdb2b4` (GEM-X pins `b12d9a3`, not in the public repo; optional, unused); sam-3d-body `b5c765a0` cloned but not installed/used |
| GEM-X env | Python 3.12.3; torch 2.12.1+cu130; torchvision 0.27.1+cu130 (sm_120 present); detectron2 0.6 built from `a1ce2f9` with CUDA_HOME=cuda-13.0, TORCH_CUDA_ARCH_LIST=12.0; onnxruntime 1.30.0 (CPU); pyzmq 27.2.0. Freeze: `venvs/gemx-freeze.txt` |
| SONIC sim env | `.venv_sim`: Python 3.10.22, mujoco 3.14.0, pinocchio 2.7.0, numpy 1.26.4 (+ torch pulled by gear_sonic deps, never used) |
| C++ build | gcc/g++ 13.3, cmake 3.28.3, `just` 1.58.0, clang 23.1.2 (conda-forge, only to satisfy deploy.sh), msgpack-cxx 6.1.1, nlohmann/json 3.11.3, ONNX Runtime 1.16.3 |
| Viewer stack | Xvfb 21.1.12 (GLX, software GL), x11vnc, noVNC + websockify (all user-level) |
| Other tools | ffmpeg 6.1.1 (system), yt-dlp 2026.8.19, uv 0.12.23 |

---

## 4. How it was built (chronological)

1. **Research (parallel agents).** Read NVIDIA's docs/code. Found: SONIC deploy needs TensorRT exactly 10.13 + CUDA; the official video path is GEM-X → `soma_to_smpl.py` → ZMQ v3; there is an official offline step (`demo_soma_onnx.py` saves `hpe_results.pt`, `soma_pt_to_sonic_v3.py` replays it).
2. **Environment (user-level, no sudo).** uv, just, yt-dlp, clang, msgpack/json/ONNX Runtime prefix; TensorRT tarball transferred by rsync (resumed once; checksum verified); GEM-X env with torch **cu130** (the README's cu126 index has no sm_120 kernels for RTX 5090, and the system `nvcc` is 13.0, which detectron2's build needs to match). Isolation verified by before/after snapshots of the driver, `/usr/local/cuda` and the home directory.
3. **Assets.** HF token placed in `$B/.env` (mode 600). SONIC checkpoint, sample motion, selective Git-LFS pulls (reference motions, G1 meshes, deploy third-party libs; the 1.6 GB motionbricks checkpoint skipped). GEM-X weights and ONNX models.
4. **SONIC deploy build.** `just build` (16 cores) after pulling `thirdparty/` LFS (the Unitree SDK `.a` was an LFS pointer).
5. **Smoke test.** Sim + deploy with the unmodified config: checkpoint loads, TRT engines build, control loop runs (policy ≈65 µs/step), reference motion completes, 0 errors. First run had the robot hanging on the elastic band (not a balance test).
6. **Band release.** `ENABLE_ELASTIC_BAND: False` crashes the sim (upstream bug: `elastic_band` attribute never created). Solution that needs no repo edit: run the sim's real MuJoCo viewer on a **virtual display** and press `9` there; view/control it through noVNC in the browser. Secured with an X cookie, a VNC password, and localhost-only ports.
7. **Clips.** Yoga: downloaded with yt-dlp (720p), cut into segments A (30–50 s), B (250–270 s), C (485–505 s) of the source and concatenated → `clip_001.mp4` (H.264, 23.976 fps, 60 s). Segment C was later found to contain a two-figure composite with captions, so replays used only A+B (`--max-frames 960`, 40 s). Dance: user video, variable frame rate (60/30 fps mix) resampled by timestamp to constant 30 fps, audio removed → `dance_001.mp4` (600 frames, 20 s).
8. **GEM-X.** `demo_soma_onnx.py -s --no-imgfeat` (static camera; 2D keypoints only, which is also what NVIDIA's live bridge forces). CPU ONNX (the plain onnxruntime wheel). ~35 min for 1443 frames, ~17 min for 600 frames. The dance's first attempt failed (container header said 798 frames, 797 decodable → ONNX concat mismatch); fixed by the CFR resample.
9. **SOMA → SMPL.** NVIDIA's `soma_to_smpl.py` crashed (CUDA index out of bounds). Root cause: it read SOMA's internal 110-name rig instead of the 78 public names (Root + 77 outputs). Fixed with a 5-line patch using `SOMALayer.public_joint_names`. Unit-tested (8 checks) and the joint mapping cross-checked against NVIDIA's own SOMA sample data (26-joint set contains all 24 mapped names).
10. **Replay.** First with NVIDIA's `soma_pt_to_sonic_v3.py` (trials 1–4): measured stream rate 14.3 fps instead of 23.976 (its loop does `publish(convert(frame)); sleep(1/fps)`, so conversion time adds to every frame). Replaced the pacing with `replay_paced.py` (convert once, publish on an absolute schedule; measured 23.98 fps, p95 jitter 44 ms) for trial 5 and all dance runs.
11. **Recording and analysis.** Screen recording of the virtual display (human clip on the left via ffplay, MuJoCo viewer on the right); a stream-capture tool records the SMPL stream and the deploy's debug stream on one clock; robot forward kinematics in MuJoCo gives limb angles/keypoints for comparison against the human skeleton; a three-panel video renders human | SMPL skeleton + robot overlay | robot.

---

## 5. How to run it again

See `docs/SETUP.md` for the environment and `README.md` for the short version. The entry points:

| Script | Purpose |
|---|---|
| `setup/clone_and_patch.sh` | NVIDIA repos at the commits used here + the converter patch |
| `pipeline/data/download_clip.sh`, `prepare_clip.sh` | download a video; cut, drop audio, constant frame rate |
| `pipeline/gemx/run_gemx.sh <clip>` | NVIDIA's offline GEM-X demo (static camera, 2D keypoints only) |
| `pipeline/sim/start_stack.sh`, `release_band.sh`, `stop_stack.sh` | virtual display + VNC + sim + deploy in tmux; release the elastic band |
| `pipeline/replay/replay_paced.py` | precompute SMPL v3 frames; publish them on an exact wall-clock schedule |
| `pipeline/replay/run_replay.sh` | streaming on, publish, screen-record, capture SMPL stream + robot state |
| `pipeline/run_demo.sh <clip> <s> <fps>` | precompute, replay, latency estimate, videos |
| `pipeline/video/make_videos.sh`, `make_gif.sh` | four panels, grid, strip; GIF |
| `analysis/angle_compare.py`, `estimate_lag.py`, `torso_analysis.py`, `plot_angles.py` | human-vs-robot comparisons |
| `tests/test_converter.py` | checks for the patched SOMA to SMPL converter |

---

## 6. Results

### 6.1 SONIC smoke test (NVIDIA reference motions)
Checkpoint loads; TRT 10.13 engines build for encoder/decoder/planner; 13 reference motions load; control loop ≈65 µs/policy step, sim state ≈1–5 ms old; motion plays to completion; 0 errors, 0 falls. First run: band on (robot hangs). With the band released through the viewer the robot stands under the policy.

### 6.2 Yoga clip (`clip_001`, 40 s replayed, side-on camera)
| Trial | Pacing | Falls | Errors | Notes |
|---|---|---|---|---|
| 1–4 | NVIDIA's offline driver, measured 14.3 fps (trial 4) | 0 | 0 | motion played ≈0.6× real speed; trial 1's video lacks the human panel (script bug) |
| 5 | `replay_paced.py`, 23.98 fps, 40.00 s | 0 | 0 | human and robot in sync; angle comparison below |

Human vs robot limb angles (trial 5, FK of measured joints vs SMPL stream; rotation-invariant):
| Angle | Human | Robot | Offset | Corr |
|---|---|---|---|---|
| elbow flexion L/R | 109°/106° | 105°/106° | −4.5°/0.1° | 0.96/0.97 |
| shoulder elevation L/R | 42°/45° | 63°/66° | +20.5°/+20.6° | 0.92/0.94 |
| knee flexion L/R | 6°/6° | 13°/13° | +7° | 0.10/0.47 |
| hip flexion L/R | 11°/10° | 18°/13° | +7°/+2° | 0.68/0.34 |
| torso lean | 1.1° | 3.6° | +2.6° | 0.16 |
Legs and torso barely move in this clip, so their low correlations are over tiny ranges. The offsets are the same with and without the pacing fix, so they are systematic.

**Diagnosis of "the pose does not look the same":** the SMPL skeleton that SONIC receives was already wrong for the profile-view clip. During prayer hands (0–20 s) its wrists are 0.60 m apart (1.5× shoulder width) when the real hands touch; 0.68 m apart during hands-behind-back. The robot's wrists were 0.54–0.61 m apart, i.e. SONIC followed its input. The converter only selects joints and rotates the frame (distance-preserving), so the error is in GEM-X's estimate. Likely cause (hypothesis, not proven): from a side-on camera the left-right direction is the camera's depth axis, which a single view barely observes.

### 6.3 Dance clip (`dance_001`, 20 s, frontal camera, one trial)
- Stream: 600 frames in 19.97 s (nominal 20.00 s), max lateness 1.5 ms. **0 falls, 0 errors.** Robot base tilt: median 5.0°, max 34.1°.
- GEM-X overlay (8 frames inspected) fits the dancer, including wide stances and bent arms; the mesh looks patchy because of the renderer, not the estimate.
- Human vs robot angles: elbow 0.88/0.90, knee 0.81/0.88, hip 0.86/0.87, shoulder elevation 0.93/0.91, torso lean 0.66 (correlations). Offsets: shoulders +22°/+24°, hips −17°/−16° (robot less flexed), torso lean −8°, elbows −5°/−4°, knees −7°/−6°. Ankle separation (robot scaled ×1.64): 0.49 m vs 0.42 m mean, corr 0.81.
- Overall mean angle error 13.7° (yoga: 8.2°). The robot reproduces a muted version of the dance.

---

### 6.4 Torso tracking (measured with `analysis/torso_analysis.py`, latency-compensated)

| Axis | Clip | Human mean (std) | Robot mean (std) | Correlation | Robot/human std |
|---|---|---|---|---|---|
| Forward lean | dance | 15.9° (6.5) | 4.6° (6.2) | 0.77 | 0.94 |
| | alien demo | 11.8° (8.8) | 5.0° (8.9) | 0.82 | 1.01 |
| Sideways lean | dance / demo | std 2.9° / 3.3° | std 6.0° / 7.9° | 0.69 / 0.79 | 2.0x / 2.4x |
| Twist | dance / demo | std 4.6° / 3.7° | std 15.4° / 4.2° | 0.27 / 0.50 | 3.4x / 1.1x |

Forward lean has the right shape and amplitude but the robot stands 7 to 11 degrees more upright. Sideways lean is exaggerated
2 to 2.4x (balance sway). Twist is poorly correlated; in the dance the waist yawed to 121 degrees for about 0.5 s during the
dancer's turn. The policy commands waist roll/pitch targets of about +-70 degrees against joint limits of +-30 degrees (the
`last_action` field is the commanded joint position), so a commanded-vs-measured gap is not a simple "motors too weak" signal.
The cause of the upright bias (policy balance priorities, the G1's short, limited waist, or the input) is not established.

Untested options, roughly cheapest first: other official SONIC checkpoints (`--sonic-v1-1`, `--low-latency`); the deploy's
`--motor-kp-scale`/`--motor-kd-scale` on the waist; an offset/gain on the torso in the streamed SMPL (a custom retarget, so a
change of scope); GEM-X with image features or `--ddim`; fine-tuning SONIC (NVIDIA's Isaac Lab training path, a separate project).

---

## 7. Checklist against the original plan (honest)

| Gate item | Status |
|---|---|
| `uv` environment works | Yes (GEM-X venv, HF venv; SONIC sim env made by NVIDIA's installer, which also uses uv) |
| SONIC checkpoint loads | Yes |
| Official smoke test passes | Yes, with the caveats in 6.1 (unit/integration checks were log-based; the first run had the band on) |
| GEM-X / SOMA unit + integration tests | Yes for execution and output shapes; perception checked visually (yoga segment C was bad and excluded; dance plausible) |
| SOMA → SMPL unit + integration tests | Yes, after the 5-line patch (8 unit checks, dry-run, ZMQ output validated) |
| SMPL → SONIC → G1 integration | Yes |
| Full video → G1 pipeline | Yes (two clips) |
| 3 repeated trials | Yoga: 5 runs (4 unpaced, 1 paced). Dance: 1 run. Not three identical dance runs |
| Side-by-side output video | Yes (screen recordings and three-panel videos) |
| `outputs/clip_001/{soma,smpl,sonic,videos}` | Yes (`smpl/` was produced later via the precompute step) |
| Source video | Source URL and segment times recorded in `data/clips/*_source.txt`; the yoga clip is a concatenation of three segments rather than one continuous 20–60 s clip |

---

## 8. Deviations from NVIDIA's official path (register)

Anything not listed here is unmodified NVIDIA code and configuration.

**Edits inside `repos/GR00T-WholeBodyControl`:** only item 1 is carried in this repo (`patches/soma_to_smpl_public_names.patch`); items 2 and 3 were local experiments.
1. `gear_sonic/examples/live_camera_teleop/soma_to_smpl.py`: 5 added lines in `_resolve_joint_names` to use `public_joint_names` (fixes the 110-vs-77 joint crash).
2. (Local experiment, not in this repo, unused by the final pipeline.) `g1_29dof_with_hand.xml`: torso camera renamed `head_camera_orig`.
3. (Same: not in this repo.) `scene_43dof.xml`: a fixed third-person camera added as `head_camera`. The final front/side views use free cameras in `render_sim_views.py` instead.

**Process/config deviations (no repo edit):**
4. `deploy.sh` is run through a user-level `clang` on PATH so its dependency step does not call `sudo apt`; it also sources ROS2 (`HAS_ROS2` on) as the script does by default.
5. Torch **cu130** instead of the README's cu126 (needed for RTX 5090 / system nvcc 13.0); torch ended at 2.12.1 because `install_env.sh` pins `setuptools<75` and uv's first resolution mismatched torchvision.
6. GEM-X run with `-s --no-imgfeat`; the plain CPU `onnxruntime` wheel (not GPU); SAM-3D-Body not used.
7. Elastic band released through the viewer on a virtual display (`ENABLE_ELASTIC_BAND: False` crashes upstream).
8. Replay uses `fps = clip fps` (23.976 / 30), not the README's 30, and `replay_paced.py` instead of NVIDIA's pacing loop (trials 1–4 used NVIDIA's loop as is).
9. Sample/reference data: selective Git-LFS pulls only.
10. Clip preparation: yoga concatenated from three segments; dance resampled to constant 30 fps.
11. Recordings are screen captures of a software-rendered viewer, not a rendered third-person camera.
12. soma-retargeter at HEAD (`cbdb2b4`) instead of GEM-X's unavailable pin `b12d9a3` (unused in the pipeline).
13. **SOMA-X is v0.3.3 (`d6aa640`), 18 commits newer than GEM-X's recorded pin `e0f8ff0`.** This was a mistake in setup (a research step misread the pin and I repeated it), not a choice. Likely consequences: (a) the 110-vs-77 joint-name crash that the `soma_to_smpl.py` patch (deviation 1) works around probably does not occur on the pinned SOMA, where the rig has the legacy 78 joints; (b) GEM-X's checkpoint was trained/exported against the older SOMA, so body-model details (skinning, identity handling) may differ slightly from what NVIDIA validated. The public 78-joint output contract is documented as stable, and the pose/skeleton results looked plausible, but the effect has not been measured. All results in this report were produced with v0.3.3.

---

## 9. Gotchas and lessons

- **Python buffers stdout when piped to a file.** A "wait for first frame" check on a log never fired; use `PYTHONUNBUFFERED=1` / `python -u`.
- **`pkill -f` / `pgrep -f` can match their own shell command line.** Kill by PID or exact name.
- **`deploy.sh` has no unattended path:** it prompts for confirmation, and needs `]` (start), `9` in the viewer (band), `T`/Enter. The scripts drive these with `tmux send-keys` and `xdotool`; the tmux window name must match (`vnc:deploy`).
- **A closed tmux window ends its process.** Avoid `Ctrl-b &`; the deploy was lost once this way.
- **micromamba writes to `~/.mamba`/`~/.conda`** even with a root prefix set; it was cleaned up. Prefer `HOME=…/tmp/agent_home` for such tools.
- **ffplay renders fine with `EGL_PLATFORM=surfaceless`**; the black human panel in the first yoga recording was only the late launch.
- **Variable-frame-rate screen recordings break GEM-X** (header vs decodable frame count); resample to constant fps first.
- **Wall-clock pacing must not include conversion time.** Precompute, then publish on an absolute schedule.
- **My own mistakes during the work** (all fixed): wrong first-guess cuts of the yoga clip, a mis-indexed hpe path, quoting slips in shell heredocs, an overwritten `out` variable, a dtype map in my subscriber. None affected delivered results except the late human panel in yoga trial 1.
- **The machine is shared** (load average ~40 on 32 cores, GPU 1 used by someone else). GEM-X on CPU is slow for that reason.

---

## 10. Open items and recommended next steps

1. **Ground-truth test (option 3, not done):** stream NVIDIA's own paired SMPL joints (`sample_data/robot_filtered/*.pkl` has `smpl_joints` next to the retargeted `dof` reference at 30 fps) through the same ZMQ path and compare the robot to NVIDIA's reference. This would show how well SONIC alone tracks known-good input, independent of GEM-X.
2. **Perception on side-on video:** try the frontal clips first, or enable image features / DDIM sampling in GEM-X (`--ddim`, SAM-3D-Body checkpoint) and re-measure wrist-to-wrist distance on the yoga clip.
3. **Test GEM-X's real SOMA pin (`e0f8ff0`):** check out that commit in `third_party/soma`, run the converter without the patch, and compare joint outputs and SONIC results against the v0.3.3 runs. This would show whether the SOMA version matters (see deviation 13).
3b. **Remove local deviations when upstream fixes them:** the `soma_to_smpl.py` patch (report upstream), and ideally a supported headless way to release the band.
4. **Repeat the dance replay** twice more if you want the "three trials" count for it.
5. **Cleanup:** stop the sim stack when done (`pipeline/sim/stop_stack.sh`); it holds a little GPU memory.
6. **Security:** the HF token file (`ENV_FILE`) and `$SONIC_WORK/tmp/vncpass.txt` stay outside the repo; never printed in logs.

---

## 11. Further reading — the upstream markdown files that explain each piece

Paths are on the remote machine under `$B/repos/…`; the same files exist on GitHub (NVlabs/GR00T-WholeBodyControl, NVlabs/GEM-X).

1. `GR00T-WholeBodyControl/docs/source/getting_started/installation_deploy.md` — TensorRT 10.13 requirement, build steps (`install_deps.sh`, `setup_env.sh`, `just build`).
2. `GR00T-WholeBodyControl/docs/source/getting_started/quickstart.md` — sim2sim in MuJoCo, the key sequence (`]`, `9`, `T`, `N/P`, `O`), controllers.
3. `GR00T-WholeBodyControl/docs/source/tutorials/zmq.md` and `…/tutorials/live_camera_teleop.md` (+ `gear_sonic/examples/live_camera_teleop/README.md`) — the ZMQ protocol v1–v4, the SMPL v3 stream, GEM-X → SONIC bridge, offline `soma_pt_to_sonic_v3.py`.
4. `GEM-X/docs/INSTALL.md` and `GEM-X/docs/DEMO.md` — environment, weights, demo arguments, outputs (`hpe_results.pt`).

Also useful: `GR00T-WholeBodyControl/docs/source/references/motion_reference.md` (reference-motion CSV format), `references/observation_config.md` (what the `smpl` encoder observes), `getting_started/download_models.md` (checkpoints and sample data), `GEM-X/docs/MODEL_OVERVIEW.md`.

---

## 12. Demonstration video (`demo_001`, added 2026-10-05)

Purpose: a stronger end-to-end demo than the yoga clip: one video in, four synchronized videos out (original, SMPL skeleton, G1 simulation front view, G1 simulation side view).

**Source and clip.** https://youtu.be/FzG4uDgje3M — the official "Dame Tu Cosita" video by El Chombo ("Dancing Green Alien", Ultra Records). The dancer is a **CGI alien, not a human** (large head, long thin limbs). Copyrighted: only the visuals are used (audio stripped); check the rights before publishing the demo. Analysis before use: 1080p, 30 fps constant; one continuous shot from 0.3 s to 98 s (only hard cut at 98.5 s, end card after 142.8 s); GEM-X's detector and 2D keypoints locked onto the alien in a 10 s test. Clip used: **2–42 s** (40 s, 1,200 frames, constant 30 fps, 1920×1080, H.264, no audio) = `data/clips/demo_001.mp4` (provenance in `demo_001_source.txt`).

**Pipeline settings (same as the other clips).** `demo_soma_onnx.py -s --no-imgfeat` (CPU ONNX, ~35 min) → `hpe_results.pt` → SOMA→SMPL (patched converter) precomputed (1,200 frames, 12.9 s) → `replay_paced.py` at 30 fps → SONIC deploy (`--input-type zmq`) → MuJoCo sim with the band already released. Orchestrated by `scripts/finish_demo.sh demo_001 40 30`.

**Results.**
- Stream: 1,200 frames in 39.97 s (nominal 40.00 s); one late frame (a 126 ms gap, 60 ms lateness) in the whole run. **0 falls, 0 errors.** Robot base tilt median 7.2°, max 21.7°.
- GEM-X overlay (8 frames inspected): the mesh follows the alien's pose (crouch, lean, arm positions); it does not cover the long limbs exactly.
- **Pipeline latency ≈ 0.38 s**: correlation of limb angles human-vs-robot is 0.59 at zero delay and 0.86 at 0.38 s (the dance clip gave 0.30 → 0.88 at the same 0.38 s). The slow yoga clip cannot resolve it.
- Limb angles at 0.38 s: correlation elbows 0.89/0.93, knees 0.90/0.90, shoulders 0.84/0.86, hips 0.78/0.81, torso lean 0.62; mean absolute error 11.5°. Offsets: shoulders +17°/+14° (robot arms more raised, as on the other clips), hips −12°/−11°, elbows −11°/−5°.

**Videos** (`outputs/demo_001/videos/final/`):
`original.mp4`, `skeleton.mp4`, `front.mp4`, `side.mp4` (each 960×540, 30 fps, 40 s, frame-synchronized), `demo_grid_2x2.mp4` (1920×1080, labelled; original | skeleton on top, front | side below) and `demo_strip_1x4.mp4` (3840×540, labelled, four across).

**How the four videos are made, and what to say about them honestly:**
1. *original* — the clip, letterboxed to 960×540.
2. *skeleton* — the 24 SMPL joints that were streamed to SONIC (from `smpl_v3_frames.npz`), drawn in a pelvis-yaw frame, front and side views.
3. *front* and 4. *side* — **re-rendered in MuJoCo from the logged state of the simulated robot** (measured joint angles + IMU orientation from `capture.npz`, `render_sim_views.py`), not screen recordings of the live viewer. Root x/y is fixed at 0 (SONIC commands no translation) and root height keeps the lowest foot on the floor, so feet and floor are plausible but not the physics engine's exact contact state. The cameras follow the robot's heading (smoothed) so "front" and "side" stay true while it turns (heading span 111° in this run). Both views come from the identical trajectory.
5. **The two sim videos are shifted earlier by the measured latency (0.38 s, stored in `sonic/trial_1/lag_used.txt`)** so they line up with the original and skeleton. Without the shift the robot would visibly lag its input by that amount.

**Scripts used:** `pipeline/run_demo.sh`, `pipeline/video/make_videos.sh`, `render_sim_views.py`, `render_skeleton_tile.py`, `analysis/estimate_lag.py`.

**Known limitations of this demo:** non-human subject (a direct human demo would be more convincing for the pipeline's intended use); mesh/skeleton accuracy is only checked visually on sampled frames; shoulder/hip offsets are systematic (section 6); the sim views are a re-render of logged state; one trial only.
