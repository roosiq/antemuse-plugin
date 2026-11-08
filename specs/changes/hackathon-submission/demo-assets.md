# Demo assets — what the 84-second cut needs

Statuses: **have** · **need** · **decide** · **not needed**.
Companion to [`demo.md`](demo.md). Nothing here changes plugin behaviour.

## A. The situation (the part that makes it real)

| asset | status | detail |
|---|---|---|
| Fixture repo with a genuinely failing test | **need** | spec in §A.1; ~6 files, deterministic failure, no network or clock |
| Opening words from the person | **need** | draft in §A.2; typed on camera, not pasted |
| The agent's follow-up request | **need** | "daydream, and close the tools" — the only instruction the agent needs |
| Clean shell prompt | **decide** | the default `bash-5.3$` is honest but noisy; a two-token prompt (`~/redwood $`) reads better. No fake hostname |
| Profile isolation for the take | **need** | throwaway `HERMES_HOME`; the live plugin must not enter a state (see `demo.md` §6) |

### A.1 Fixture repo — `redwood`

A tiny CSV exporter whose empty-result path is broken. The failure is the setup
for the whole video: three hours on a red test.

```
redwood/
  README.md
  redwood/__init__.py
  redwood/export.py
  tests/test_export.py
```

`redwood/export.py`:

```python
def export(rows, columns=("id", "name")):
    """Render rows as CSV, header first."""
    if not rows:
        return ""                      # the bug: an empty result has no header
    lines = [",".join(columns)]
    lines += [",".join(str(r[c]) for c in columns) for r in rows]
    return "\n".join(lines) + "\n"
```

`tests/test_export.py`:

```python
from redwood.export import export


def test_export_writes_header():
    assert export([{"id": 1, "name": "Ada"}]) == "id,name\n1,Ada\n"


def test_export_handles_commas():
    assert export([{"id": 2, "name": "Smith, John"}]) == 'id,name\n2,Smith, John\n'


def test_export_writes_header_when_there_are_no_rows():
    assert export([]) == "id,name\n"


def test_export_keeps_column_order():
    assert export([{"name": "Ada", "id": 1}]) == "id,name\n1,Ada\n"
```

Git history: three commits (`init`, `export`, `test: empty result still needs a
header`). The third commit is red on purpose and is the commit on screen.

Expected on-camera output: `1 failed, 3 passed` with the failing test named.

### A.2 Opening words

> i've been on this for three hours and the export test still fails. something is
> off with the empty case.

Then, after `/break`:

> daydream, and close the tools

Both are typed with `human_type.py --via xdotool` (one seeded typo, corrected).

## B. What is on screen

| asset | status | detail |
|---|---|---|
| Live scene renderer | **have** | `node tools/term_scene.cjs`; verified today: `daydream 56x32 lit=299` in 40 ms, no Chromium, no baked PNG bank |
| Baked frame bank (`three_frames/`) | **not needed** | the old Chromium path needs `chromium-browser` and a static server; the live rasteriser is the path |
| Scene coverage for the four states | **have** | `walk`, `daydream`, `doomscroll`, `dream` all declare a `scene` key; only `daydream` is shot in the video |
| Keystroke pill styling | **have** | `screenkey`, amber `#f2b25a` on ground, verified in a take |
| Pointer | **have (small)** | real I-beam, ~24 px, captured by `x11grab`; optional 40 px ring is **decide** (H49) |
| Caption cards (9) | **have** | `tools/demo/out/beat_*.png`, brand palette, regenerable from `beats.json` |
| End card data | **need** | repo URL is known; **catalog PR number is not** — fill after the PR opens |

## C. Sound

| asset | status | detail |
|---|---|---|
| Voiceover | **not needed** | X autoplays muted; TTS would read as generated |
| Music bed | **decide** | none is safest; if used, one licensed track at −22 LUFS under the cut and no claims made by it |
| Spoken intro (optional) | **decide** | only Ryan's own 20–30 s recording, added under the captions |

## D. Publication and catalog assets

| asset | status | detail |
|---|---|---|
| X post copy | **need (draft exists)** | one sentence + `@NousResearch`; thread reply carries the catalog PR |
| Alt text for the video | **need** | 1–2 sentences describing what is shown, for accessibility |
| Caption file (`.srt`) | **need** | burned-in captions are in the pixels; a sidecar `.srt` is still worth shipping |
| Cover still (1280×720) | **need** | one frame with the takeover and a caption; X shows it before play |
| Catalog screenshots (up to 6) | **need** | 4 planned: takeover, chat postcard, `/break`, blocked-tool refusal; commit under `docs/screenshots/` at the pin |
| Catalog banner (2:1, 1200×600) | **decide** | optional `image:` field; the entry reads fine without one |
| Repo description / README first screen | **have (draft)** | README opening is written; refresh after the pin |

## E. Provenance and legal

| asset | status | detail |
|---|---|---|
| Meshy asset manifests | **have** | `data/meshy/*/manifest.json` record provider, licence, task id, sha256, triangle count |
| three.js licence | **have** | MIT, bundled under `tools/` and `node_modules` at install |
| Open Collider attribution | **have, unused here** | CC BY 4.0, `data/collider/ATTRIBUTION.md`; no collider material appears in the demo |
| Font licence | **have** | Liberation Mono, SIL OFL, present on the system |

## F. Repo weight before the pin

`data/meshy/` is **39 MB in the working tree but only 636 KB tracked** — 12 files:
the per-state manifests and three GLBs. The bulk is `data/meshy/pack/`, which is
untracked and covered by the `data/meshy/` ignore rule, so it stays out of the pin.
Nothing needs pruning; the pin should simply be checked with
`git ls-files data/meshy | xargs du -ch` and kept at the tracked set.

The live renderer does not read the packs anyway: `tools/term_scene.cjs` programs
the scenes in code, and it has no `meshy`/`glb`/`pack` reference.

## G. Delivery set

```
demo.mp4          84 s, 1280x720, H.264, < 12 MB
demo.srt          same captions, sidecar
cover.png         1280x720 still
shots/            4 catalog screenshots at the pin
```

## What is missing, ranked

1. Fixture repo and its three-commit history (§A.1).
2. End-card PR number (blocked on the catalog PR).
3. Cover still and the four catalog screenshots.
4. X copy, alt text, `.srt`.
5. Decisions: prompt styling, music, pointer ring, and the 39 MB pack.
