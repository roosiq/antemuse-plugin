#!/usr/bin/env python3
"""End to end with a real mouse and a real keyboard: the states, the cockpit, the map.

The states are entered and stepped by the real engine; the map it produces is built from the
ledger's own served rows (labels, weights, trail). That map is then handed to the shipped
`createCockpit` inside Chromium, where every interaction is a real browser event: mouse drags,
clicks, and key presses. Nothing here is a fixture standing in for the engine.

    env -u PYTHONPATH PLAYWRIGHT_BROWSERS_PATH=0 uvx --with playwright --with nltk \
        --quiet python tools/input_e2e.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("ANTEMUSE_STATES_HOME", tempfile.mkdtemp(prefix="input-e2e-"))

import cockpit_harness as ch  # noqa: E402
from activation_render import coords_for  # noqa: E402
from core import activation, engine, recall, states  # noqa: E402

SEED = (
    "A recorded turn with enough words for one memory.",
    "Another recorded turn with enough words for another memory.",
    "A third recorded turn lets two memory pairs remain distinct.",
)


def served_labels() -> list[str]:
    """The concepts this state actually served, in order, from the ledger."""
    rows = activation._rows(
        "SELECT c.label FROM served s JOIN concepts c ON c.id = s.concept_id "
        "ORDER BY s.at ASC")
    return [r[0] for r in rows if r[0]]


def payload_for(key: str, labels: list[str]) -> dict:
    """The map the pane would draw: real served concepts, real positions, real trail."""
    labels = labels[-60:]
    coords, _ = coords_for(labels)
    nodes, seen = [], {}
    for label in labels:
        if label in seen:
            continue
        seen[label] = True
        pt = coords.get(label) or (0.0, 0.0, 0.0)
        x, y, z = (list(pt) + [0.0, 0.0, 0.0])[:3]
        nodes.append({"l": label, "x": x, "y": y, "z": z,
                      "w": min(1.0, 0.45 + 0.15 * labels.count(label)), "v": 0.5})
    links = [{"a": a, "b": b, "w": 2} for a, b in zip(labels, labels[1:]) if a != b]
    return {"key": key, "nodes": nodes, "links": links, "path": labels[-8:],
            "lit": len(nodes)}


def main() -> int:
    for line in SEED:
        recall.remember(line)

    tmp = Path(tempfile.mkdtemp(prefix="input-e2e-page-"))
    shots = Path(tempfile.mkdtemp(prefix="input-shots-"))
    shutil.copy(ROOT / "desktop" / "plugin.js", tmp / "plugin.js")
    (tmp / "sdk.js").write_text(ch.SDK_STUB)
    (tmp / "react.js").write_text(ch.REACT_STUB)
    (tmp / "jsx.js").write_text(ch.JSX_STUB)
    (tmp / "graph.js").write_text("window.__live = null; window.__makeGraph = () => window.__live;")
    (tmp / "index.html").write_text(
        ch.PAGE.replace('<script type="module">',
                        '<script src="./graph.js"></script>\n<script type="module">'))

    httpd, url = ch.serve(tmp)
    from playwright.sync_api import sync_playwright

    rows = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 960, "height": 620}, device_scale_factor=2)
        errors: list[str] = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url, wait_until="load")
        page.wait_for_function("window.__ready === true", timeout=20000)

        cv = page.evaluate("() => { const r = document.getElementById('cv').getBoundingClientRect();"
                           " return {x: r.x, y: r.y, w: r.width, h: r.height} }")

        for key in states.STATES:
            said = engine.enter(key, session="input")
            entered = not said.startswith("cannot enter")
            block = ""
            if entered:
                for _ in range(int((states.STATES[key].get("dose") or {}).get("n") or 1)):
                    engine.note_turn("input")
                    block = engine.inject("input") or block
                labels = served_labels()
            else:
                labels = []

            payload = payload_for(key, labels)
            page.evaluate("(p) => { window.__live = p; "
                          "if (window.__cockpit) window.__cockpit.destroy(); window.__mk({}); }", payload)
            page.wait_for_timeout(350)
            before = page.evaluate("__cockpit.stats()")

            # real mouse: drag across the map. The cockpit captures the pointer on press —
            # "the mouse does nothing" and "the mouse is steering a ship that is not moving"
            # look identical, so the observable is ownership plus a target, not a guess.
            page.mouse.move(cv["x"] + cv["w"] * 0.5, cv["y"] + cv["h"] * 0.5)
            page.mouse.down()
            for i in range(10):
                page.mouse.move(cv["x"] + cv["w"] * (0.5 + 0.03 * i),
                                cv["y"] + cv["h"] * (0.5 - 0.01 * i))
            turned = page.evaluate("__cockpit.stats()")
            page.mouse.up()
            page.wait_for_timeout(120)

            # real mouse: click where the map is
            page.mouse.move(cv["x"] + cv["w"] * 0.45, cv["y"] + cv["h"] * 0.4)
            page.mouse.down()
            page.mouse.up()
            page.wait_for_timeout(150)
            clicked = page.evaluate("__cockpit.stats()")

            # real keyboard, with the canvas focused the way a click focuses it
            page.locator("#cv").focus()
            for k in ("a", "d", "f"):
                page.keyboard.press(k)
            page.wait_for_timeout(150)
            keys = page.evaluate("__cockpit.stats()")

            shot = shots / f"{key}.png"
            page.locator("#cv").screenshot(path=str(shot))
            # Escape frees the mouse and stays (0.11.14 decided that); the drawn button is the
            # one that leaves. Test the control that is supposed to leave.
            page.keyboard.press("Escape")
            page.wait_for_timeout(120)
            freed = page.evaluate("__cockpit.stats()")
            page.locator("#exit").click()
            page.wait_for_timeout(200)
            exited = page.evaluate("window.__exited || 0")

            engine.stop("input", reason="dose")
            rows.append({
                "state": key,
                "entered": entered,
                "nodes": before.get("nodes"),
                "lit": before.get("lit"),
                "path": before.get("path"),
                "pointer_on_drag": bool(turned.get("pointer")),
                "target": clicked.get("target") or turned.get("target"),
                "picks": (before.get("picks"), clicked.get("picks")),
                "shots": (before.get("shots"), keys.get("shots")),
                "hits": keys.get("hits"),
                "pointer_after_esc": bool(freed.get("pointer")),
                "exited": exited,
                "errors": errors[-2:],
                "shot": str(shot),
            })
        browser.close()
    httpd.shutdown()

    print(f"{'state':<11} nodes  lit  path  drag  target            picks      shots    esc")
    for r in rows:
        print(f"{r['state']:<11} {str(r['nodes']):>5}  {str(r['lit']):>3}  {str(r['path']):>4}  "
              f"{str(r['pointer_on_drag']):<5}  {str(r['target'])[:16]:<16}  "
              f"{str(r['picks']):<9}  {str(r['shots']):<7}  esc→pointer={r['pointer_after_esc']} "
              f"button={r['exited']}")
        if r["errors"]:
            print(f"    console: {r['errors']}")
    print(f"\nshots: {shots}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
