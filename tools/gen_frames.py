#!/usr/bin/env python3
"""Render the state scenes as real images with the local SD server.

    python3 tools/gen_frames.py --state walk --count 6
    python3 tools/gen_frames.py --all --count 6

Writes <data>/real/<state>/f000.png ... at 768x384, letterbox cropped. The
terminal only ever shows these downsampled to ~100x52 pixels, so composition
and colour matter and fine detail does not.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import pathlib
import sys
import time
import urllib.request

from PIL import Image

SERVER = os.environ.get("SD_SERVER", "http://100.82.186.41:8089")
DATA = pathlib.Path(os.environ.get(
    "ANTEMUSE_STATES_HOME", os.path.expanduser("~/.hermes/plugin-data/antemuse")))

NEGATIVE = ("text, watermark, signature, logo, caption, letters, cartoon, anime, "
            "3d render, oversaturated, hdr halo, border, frame, collage")

SHOTS = ("wide cinematic 35mm photograph, shallow depth of field, natural light, "
         "film grain, muted colour, no people looking at camera")

# Each state gets several takes so the screen can drift between them.
PROMPTS = {
    "walk": [
        "lone figure seen from behind walking away down a wet empty road toward a huge low amber sun at dusk",
        "person walking alone along a sea wall at dawn, teal water, heavy sky, back to camera, small in frame",
        "single walker on a forest track at blue hour, mist between bare trees, faint warm light ahead",
        "solitary man walking down a rain-slicked city pavement at night, distant warm windows, long reflection",
        "figure crossing an empty moor toward a low sun, wind bent grass, cold blue sky",
        "lone woman walking away across a wide beach at low tide, wet sand mirroring a pale sun",
    ],
    "daydream": [
        "empty sunlit room, dust drifting in a shaft of afternoon light, curtain lifting, warm haze",
        "close detail of a window with rain on glass, soft bokeh lights beyond, warm interior glow",
        "quiet kitchen table in half light, a cooling cup, long shadows, memories of a place once lived in",
        "soft focus field of tall grass in summer wind, sun flare, dreamy overexposure",
        "stairwell at dusk, one warm lamp, worn banister, long soft shadows",
        "bedroom ceiling with light from a streetlamp moving slowly across it, dust, quiet",
    ],
    "dream": [
        "surreal double exposure of a forest and a sleeping face, deep indigo and violet, dissolving edges",
        "impossible architecture, staircases bending into water, moonlight, deep blue dream landscape",
        "two moons over a still black sea, faint gold reflection, strange calm, surreal photograph",
        "a room melting into a field, furniture half submerged in grass, violet twilight, dreamlike",
        "figure with no face standing in a corridor of doors, cold blue light, unsettling quiet",
        "clouds shaped like rooms, interior weather, dark purple sky, dream photograph",
    ],
    "doomscroll": [
        "extreme close up of a man's face in the dark, lit from below by the cold blue glow of a phone he is holding, eyes open, mouth slack, no other light",
        "over the shoulder shot of a woman scrolling a phone in a pitch dark room, blue screen light on her face, thumb on the glass, black background",
        "a phone screen glowing in total darkness, scrolling text blurred into streaks, a hand holding it, face barely lit behind it",
        "face lit by a laptop screen at night, blue white light from below, deep black room, eyes fixed, exhausted",
        "two people on a dark bus, both faces lit blue by phones, night outside, no conversation",
        "close up of bloodshot eyes above a bright phone screen, blue glow, darkness everywhere else, insomnia",
    ],
}

ASPECT_W, ASPECT_H = 768, 384


def _post(payload: dict, timeout: int = 600) -> dict:
    req = urllib.request.Request(
        SERVER + "/sdapi/v1/txt2img",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _decode(payload: dict) -> Image.Image:
    images = payload.get("images") or []
    if not images:
        raise RuntimeError("server returned no images")
    raw = images[0]
    if raw.startswith("data:"):
        raw = raw.split(",", 1)[1]
    return Image.open(io.BytesIO(base64.b64decode(raw))).convert("RGB")


def _crop_letterbox(im: Image.Image) -> Image.Image:
    """SD pads wide frames with black bars; drop uniform dark rows/columns."""
    g = im.convert("L")
    rows = [i for i, v in enumerate(g.resize((1, g.height), Image.BOX).getdata()) if v > 6]
    cols = [i for i, v in enumerate(g.resize((g.width, 1), Image.BOX).getdata()) if v > 6]
    if len(rows) < 8 or len(cols) < 8:
        return im
    return im.crop((cols[0], rows[0], cols[-1] + 1, rows[-1] + 1))


def render(state: str, index: int, out_dir: pathlib.Path,
           steps: int = 22, seed: int | None = None) -> pathlib.Path:
    prompts = PROMPTS[state]
    prompt = f"{prompts[index % len(prompts)]}, {SHOTS}"
    use_seed = index * 977 + 11 if seed is None else seed
    started = time.time()
    payload = _post({
        "prompt": prompt,
        "negative_prompt": NEGATIVE,
        "width": ASPECT_W,
        "height": ASPECT_H,
        "steps": steps,
        "cfg_scale": 7,
        "seed": use_seed,
        "sample_method": "euler_a",
    })
    im = _crop_letterbox(_decode(payload))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"f{index:03d}.png"
    im.save(path)
    print(f"{state} {path.name} {im.width}x{im.height} {time.time() - started:.1f}s seed={use_seed}",
          flush=True)
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", action="append", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--count", type=int, default=6)
    ap.add_argument("--steps", type=int, default=22)
    ap.add_argument("--out", default=str(DATA / "real"))
    args = ap.parse_args()

    states = list(PROMPTS) if args.all else args.state
    if not states:
        ap.error("give --state or --all")

    for state in states:
        if state not in PROMPTS:
            ap.error(f"unknown state {state}")
        out_dir = pathlib.Path(args.out) / state
        for i in range(args.count):
            render(state, i, out_dir, steps=args.steps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
