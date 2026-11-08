"""What the plugin costs, measured where it now lives."""
from __future__ import annotations

import json
import os
import statistics
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
os.environ["ANTEMUSE_STATES_HOME"] = "/home/ryan/.hermes/cache/scratch/bench"
os.environ.setdefault("NLTK_DATA", "/home/ryan/nltk_data")

t0 = time.perf_counter()
from core import engine, mood, panel, photographs, states, storage, tui  # noqa: E402
IMPORT_S = time.perf_counter() - t0


def bench(label, fn, n=50):
    fn()                                   # warm
    samples = []
    for _ in range(n):
        s = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - s) * 1000)
    print(f"{label:34} median {statistics.median(samples):7.2f} ms   p95 {sorted(samples)[int(n*0.95)-1]:7.2f} ms")
    return statistics.median(samples)


def state():
    return {"active": {"key": "walk", "label": "WALKING", "turns_left": 4,
                       "ends_at": time.time() + 600, "total_seconds": 1800,
                       "seconds_left": 600, "contract": "work continues",
                       "tools": None},
            "journal": [{"who": "state", "state": "walk", "event": "walk",
                         "text": f"hand (n) → palm (n) · took its meronym · step {i}",
                         "at": time.time()} for i in range(40)],
            "residue": []}


print(f"import time (module load)         {IMPORT_S*1000:7.1f} ms")
print()

engine.clear()
engine.enter("walk", 30)
bench("inject() — per turn", engine.inject)
bench("policy() — per tool call", lambda: engine.policy("terminal"))
bench("note_turn() — per turn (writes)", engine.note_turn)
bench("annotate() — per reply", lambda: engine.annotate("a reply"))
print()

for cols, rows in ((80, 24), (120, 40)):
    ms = bench(f"tui.imagery_frame {cols}x{rows}", lambda: tui.imagery_frame(state(), cols, rows, 5), n=20)
    print(f"{'':34} → {1000/ms:5.1f} fps ceiling")
    ms = bench(f"panel.debug {cols}x{rows}", lambda: panel.debug(state(), w=cols, color=True), n=20)
print()

engine.enter("walk", 30)
engine.stop()
engine.enter("daydream", 3)
engine.stop()
print("account line:", engine.stop() if engine.peek() else "(already ended)")
print("break view  :", json.dumps(engine.break_view()))
print("data dir    :", storage.data_dir())
print("states      :", ", ".join(f"{k}:{v['minutes']}m/{v['cadence']}s" for k, v in states.STATES.items()))
print("photo counts:", photographs.counts())
print("mood helpers:", len(mood.SUGGEST), "feelings mapped")
