# Plan: scenes-per-surface

Companion to `spec.md`. Every number here is measured on this machine, not
aspirational.

## Current state

- `core/realimagery.py`: photographs from `<data>/real/<state>/*.png`,
  two pixels per cell (`▀` fg=top, bg=bottom), global `HOLD_S=11`, `FADE_S=2.4`,
  one drift oscillation over 26 s, Bayer-8 dissolve.
- `core/surfaces.py`: `PROFILES` per client; terminal `animate: true`, chat
  `image: true` but still rendering ASCII art from `three_frames`.
- `tools/gen_frames.py`: 768×384 SD1.5 renders at 22 steps, ~9.5 s each, six per
  state, letterbox-cropped.
- `tools/term_scene.cjs`: live three.js fallback, used only when a state has no
  photographs.

## Decisions

### D1 — motion is a property of the state

| state | hold | fade | motion |
|---|---|---|---|
| walk | 9.0 s | 3.0 s | drift + slow push-in, dissolve |
| daydream | 12.0 s | 3.5 s | drift only, dissolve |
| dream | 24.0 s | 5.0 s | very slow drift, long dissolve |
| doomscroll | 2.2 s | 0.35 s | hard cut, 1-cell vertical jitter, push-in |

Rationale: dream is 30 minutes and dissolves are its whole texture; doomscroll is
a firehose and must never settle. One shared profile made all four states feel
like the same screensaver.

### D2 — the clock is a grade, not new renders

`g = elapsed / total`, clamped. Applied to the downsampled cells (O(cells), not
O(pixels), so it is free at 10 fps):

- exposure: `1 + 0.15 * (g - 0.5)` for walk (dusk → darker), inverse for daydream
- warmth: lerp channel gains toward amber by `0.12 * g` (walk), toward violet by
  `0.10 * g` (dream)
- veil: blend to the state's fog colour by `0.18 * g` (walk), `0.10 + 0.12 * g`
  (dream), 0 (doomscroll)

Deterministic from `(elapsed, duration)`, so two windows showing the same state
agree (R8) and nothing needs re-rendering.

### D3 — two scores, computed where the picture is used

- `terminal_score(path)`: downsample to the terminal grid (100×52), greyscale.
  Score = 0.5 · (distinct luminance bands / 8) + 0.5 · (p95 − p5)/255, with a
  hard reject when bands < 3. This is what brightness alone got wrong: a pale
  wall scores high and shows nothing.
- `chat_score(path)`: at full size, contrast minus a clipping penalty
  (`fraction of pixels ≥ 250 or ≤ 5`, weight 1.5).

Both written to `<data>/real/scores.json` keyed by path + mtime, so scoring runs
once per generated frame, not per draw.

### D4 — chat gets a postcard

`surfaces.postcard(state)` → 4:5 crop (720×900), centred but biased 12% below
centre so a walking figure and the horizon both survive the crop. Saved under
`<data>/postcards/<state>-<index>.png`. Returned as `MEDIA:<path>` with no text
beside it.

Emission rules:

- entry: the `/walk`-style command response carries the postcard
- resolution: `stop()`'s tool result carries it
- midpoint: only for states longer than 15 minutes, and the ticker may not open
  a message of its own. It sets a pending flag; the next agent turn's injected
  block says `[A POSTCARD IS WAITING — include MEDIA:<path>]`. Rides existing
  turns instead of spawning messages.

### D5 — the wide strip never leaves the terminal

Chat crops from the same 768×384 render. Terminal keeps the 2:1 framing. No
second render is required — the render has enough height for both crops.

### D6 — the old ASCII bank is retired for image-capable profiles

`surfaces.card()` keeps its text card for `text` and terminal profiles. Chat
profiles with `image: true` stop drawing ASCII art and start attaching
postcards. `tools/term_scene.cjs` remains the terminal fallback.

### D7 — the carried-over spec item

`state-return-report`'s open question resolves to **yes**: walk accounts name the
relation. Format inside the existing trail:
`body part → loins [hyponym] → torso [holonym]`, capped at five heads as today.
Rejected: renaming the relations to plain English — WordNet's names are the
material and the agent can gloss them.

### D8 — origin binding, by construction

The plugin never sends. It only returns strings — hook context, command output,
tool results — and Hermes routes those back to the turn that produced them. That
gives origin binding for free, provided three things hold:

1. No delivery helper exists. Nothing in `core/` calls a gateway send API or
   names a channel; `surfaces.py` stays a pure encoder.
2. Entry records its origin: `{session_id, platform, project}` on the active
   state, captured from `pre_llm_call(session_id=…, platform=…)` — the hook
   passes `session_id`, `task_id`, `turn_id`, `sender_id`, and `parent_session_id`
   but **not** `chat_id`, so session identity is the strongest handle available.
   Chat routing is the gateway's job and needs no chat id from us.
3. A pending postcard is gated on `session_id` equality at delivery time and
   dropped when the session's state ends.

`project` is the nearest ancestor containing `.git` from the working directory at
entry; artifacts go to that project's `.antemuse/` when `ANTEMUSE_STATES_HOME` is
unset, and the global data dir otherwise. The state record itself stays single
and global — policy is agent-wide, and a second copy per project would let the
agent walk in one directory and be free in another.

Rejected: passing chat ids through plugin config. It would work, but it makes
the plugin responsible for routing, which is exactly the coupling this design
avoids.

## Risks

- **Frame selection can still pick a subjectless frame.** D3 fixes brightness
  ranking but not semantics: a high-contrast wall is not a walk. Mitigation:
  generate 8 per state instead of 6 and let the terminal score pick; accept that
  a human glance is still required once per batch.
- **Grade on cells is cheap but banded.** Ordered dithering already limits
  precision to 64 levels; the grade must be applied *before* the dither partner
  is chosen or the veil will look like a checkerboard. Apply grade to the 8-bit
  cell values, then render.
- **Postcard size.** 720×900 PNG ≈ 300–700 KB per state; six states' worth is
  fine, but they must be gitignored, not committed.
- **Shared state file.** Any live test writes `state.json` in the real data dir
  and can lock the agent's own tools (happened during the last session). All
  verification runs use `ANTEMUSE_STATES_HOME=/tmp/...`.

## Verification strategy

1. Pure functions first: motion profile lookup, grade math, both scores, crop
   geometry — unit tests with fixed inputs, no images on disk.
2. Image integration: a 3-frame temp bank in `ANTEMUSE_STATES_HOME`, asserting
   cell counts, dissolve monotonicity, and that no `[A-Za-z]{2,}` reaches a row.
3. Live terminal: `tmux` capture, ANSI parsed back to pixels, two captures ≥ 60 s
   apart must differ in mean luminance by ≥ 12 (R2).
4. Chat: `surfaces.postcard()` output opened and checked for size, aspect, and
   absence of text; one vision pass per state to confirm it is a photograph of
   the right thing.
5. Full suite: `uvx --with pillow --with nltk --quiet pytest tests/ -q`.
