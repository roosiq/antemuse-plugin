"""CLI for the ambient screensaver scenes.

The renderer lives in `core/screensaver.py` so the pane and the CLI cannot drift.

Run:  python3 tools/screensaver.py walk 1 58x22
      python3 tools/screensaver.py --save
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from core import screensaver as S  # noqa: E402


def main() -> None:
    if "--save" in sys.argv:
        out = pathlib.Path(__file__).resolve().parent.parent / "docs" / "brand" / "screensaver"
        out.mkdir(parents=True, exist_ok=True)
        for st in ("walk", "daydream", "dream", "doomscroll", "idle", "work"):
            frames = S.scene(st, 3, 64, 26)
            path = out / f"{st}-64x26.txt"
            path.write_text("\n".join("   ".join(f[r].ljust(64) for f in frames)
                                      for r in range(26)), encoding="utf-8")
            print(path)
        return
    state = sys.argv[1] if len(sys.argv) > 1 else "walk"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    size = next((a for a in sys.argv[1:] if "x" in a and a[0].isdigit()), None)
    w, h = (int(v) for v in size.split("x")) if size else (58, 22)
    frames = S.scene(state, n, w, h)
    if "--strip" in sys.argv:
        for r in range(h):
            print("   ".join(f[r].ljust(w) for f in frames))
    else:
        for i, f in enumerate(frames):
            print(f"-- {state} frame {i}")
            print("\n".join(f))
            print()


if __name__ == "__main__":
    main()
