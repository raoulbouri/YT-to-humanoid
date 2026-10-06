"""Record the SMPL v3 stream and the deploy debug stream (topic g1_debug) with one clock, for later analysis."""
import zmq, msgpack, json, time, signal, sys, argparse
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--seconds", type=float, default=120)
ap.add_argument("--pose-port", type=int, default=5556); ap.add_argument("--debug-port", type=int, default=5557)
a = ap.parse_args()
ctx = zmq.Context(); p = ctx.socket(zmq.SUB); p.connect(f"tcp://127.0.0.1:{a.pose_port}"); p.setsockopt(zmq.SUBSCRIBE, b"pose")
d = ctx.socket(zmq.SUB); d.connect(f"tcp://127.0.0.1:{a.debug_port}"); d.setsockopt(zmq.SUBSCRIBE, b"g1_debug")
pt, pidx, pj, pq = [], [], [], []
st, sidx, bq, bqt, bqu, act = [], [], [], [], [], []
DT = {"f32": "<f4", "f64": "<f8", "i32": "<i4", "i64": "<i8"}
stop = False
def _s(*_): 
    global stop; stop = True
signal.signal(signal.SIGINT, _s); signal.signal(signal.SIGTERM, _s)
poll = zmq.Poller(); poll.register(p, zmq.POLLIN); poll.register(d, zmq.POLLIN)
t0 = time.time()
while not stop and time.time() - t0 < a.seconds:
    for s, _ in poll.poll(100):
        t = time.time(); m = s.recv()
        if s is p:
            h = json.loads(m[4:1284].rstrip(b"\x00").decode()); body = m[1284:]; off = 0; f = {}
            for fl in h["fields"]:
                dt = np.dtype(DT.get(fl["dtype"], fl["dtype"])); n = int(np.prod(fl["shape"])) * dt.itemsize
                f[fl["name"]] = np.frombuffer(body[off:off+n], dtype=dt).reshape(fl["shape"]); off += n
            pt.append(t); pidx.append(int(f["frame_index"].ravel()[0])); pj.append(f["smpl_joints"].reshape(24, 3)); pq.append(f["body_quat"].ravel())
        else:
            x = msgpack.unpackb(m[len(b"g1_debug"):], raw=False)
            st.append(t); sidx.append(x["index"]); bq.append(x["body_q"]); bqt.append(x["body_q_target"]); bqu.append(x["base_quat"]); act.append(x["last_action"])
np.savez(a.out, pose_t=pt, pose_idx=pidx, smpl_joints=np.array(pj), smpl_body_quat=np.array(pq), state_t=st, state_idx=sidx, body_q=np.array(bq), body_q_target=np.array(bqt), base_quat=np.array(bqu), last_action=np.array(act))
print("saved", a.out, "pose msgs", len(pt), "state msgs", len(st), flush=True)
