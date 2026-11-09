# Change: the concept map as the state visual — activations while a state fires

Status: **PARTIAL** · opened 2026-11-08 · computation and renderer built 2026-11-08

## Intent

Ryan asked: *"could we use this as our state visualization, where we show activations of the
concepts when they're firing in the states?"*

The answer is yes, and the pieces already exist to do it honestly: every state serving is in the
ledger with its move, session and timestamp, and the concept map already has deterministic
semantic coordinates. What was missing is the middle layer — turning servings into a weight that
decays, so a picture can show what is live *now* rather than what has ever happened.

## What is built

**`core/activation.py`** — activation as arithmetic, no model:

- `activations(session, move, now)` → concept → weight in 0..1, `exp(-age/half_life·ln2)` with a
  180 s half-life and a 0.25 floor;
- the **freshest sighting wins** rather than summing: a word repeated all day must not outrank one
  firing right now;
- a serving **later than `now` is not active** — without that bound every concept lights up in the
  first frame of a long session;
- the time bound lives in the SQL, not after the `LIMIT` (filtering the newest 600 rows by time
  made every early frame empty);
- `sequence()` takes frames at the **real serving timestamps**, evenly sampled: sessions are
  bursty, and evenly spaced clock time spends most frames on the gaps between turns;
- `hot()` and `summary()` for what the sequence was about.

**`core/activation_stills.py`** — the map for the desktop pane, which is a picture surface:

- three JPEG stills (960×600) at three moments of the state's arc, cached 45 s and regenerated
  when stale, because a state's arc is seconds long and three moments are the story;
- `GET /api/plugins/antemuse/state` returns them as `stills`; `GET /art/{state}/{file}` serves
  only files the plugin wrote, matching both segments rather than joining user input, and refusing
  with a 404 rather than a 200 that explains itself;
- a state with no servings of its own in this session draws the session's firings instead of an
  empty field — a walk entered a minute ago has no `walk` rows yet;
- the pane paints them through the cross-fading `<img>` layers it already uses for the baked
  scenes, and falls through to the baked art when the list is empty;
- **no ASCII** — an earlier glyph path was built and removed on instruction: the pane shows a
  picture.

**The look is three.js, at bake time.** `tools/activation_post.html` puts a still through the
official `EffectComposer` — bloom, chromatic separation, grain, vignette, `OutputPass` — and
`tools/postprocess_activation.py` drives it in headless Chromium via `tools/shoot.mjs`. Three is
vendored under `vendor/three-bake/` (r180) and the plugin itself imports none of it: bake time
only, as the architecture requires. A still that fails to render keeps its plain version, named on
stderr, because a missing effect is not a reason to lose the picture.

**`tools/activation_render.py`** — the picture: the semantic map dimmed, active concepts lit with
a blurred glow, radius and brightness by weight, and **no text anywhere**. `--move` restricts to
one state, `--gif` animates, and a one-row strip is always written.

Measured on the real ledger: the session of 2026-11-08 09:18 renders as a 10-frame arc with
**263 concepts touched and 66 concurrently lit at the peak** — it rises, breathes and fades,
which is what a state looks like from outside.

## What is not built

**The pane does not draw this yet.** Wiring it means a new scene in the desktop pipeline
(`desktop/art` frames → `core/surfaces.py` → `desktop/plugin.js`), and that directory currently
carries an unrelated art reorganization (80 dirty paths the owner asked to leave alone). The
renderer writes PNG/GIF frames that pipeline can consume; the scene registration and the frame
budget per surface are the remaining work. Until then this is a tool, not a surface.

### The wiring, specified so it can be picked up cold

Recorded in `docs/spec.md` §17.2 as well, because that is where unwired work lives.

1. **Registration.** `activation` becomes a scene in `core/surfaces.py` and `desktop/plugin.js`,
   selected by the active state (`?state=walk`), so it needs no setting. A setting may change how
   loud or how long a state is; it may not change what a state is — and the scene is what a state
   looks like, not how loud it is.
2. **Frame budget per surface.** Terminal: quantised frames at ~2 fps, like the baked scenes.
   Chat: one still on entry, the strip at the edge. Desktop pane: the GIF.
3. **No text, in every encoding.** The no-words rule (`§10.1`) holds on the card path exactly as
   it holds on the PNG: `tests/test_activation.py::test_the_picture_carries_no_words` guards the
   renderer, and the scene must not add a caption to satisfy a legend.
4. **Empty ledger is a named fallback.** A state with no servings falls back to its baked scene
   and says so, rather than drawing an empty field.
5. **Determinism.** Same ledger, same moment, same frame — the coordinates come from the
   embedding projection and the weights from arithmetic, so a captured frame can be re-derived
   and compared.

Acceptance for the wiring: entering a state draws the activation scene within one turn; leaving
it stops the animation; a missing ledger or a session with no servings draws the named fallback;
and the capture used as evidence is reproducible from the ledger.

Nothing here enters a state, changes a dose, or adds a command or a setting.

## Acceptance criteria

1. Weight halves over one half-life and falls below the floor when cold.
2. A serving in the future is not active.
3. Repetition does not outrank recency.
4. `--move` narrows the map to that state; without it, every serving counts.
5. `sequence()` produces a frame at real moments and every frame of a spread-out session has
   activity.
6. The renderer draws no text — asserted against the source, because the human card is a picture.
7. Missing ledger, unknown session or no vectors: a named message, never a traceback.
8. Frames are deterministic for the same ledger and moment.

## Verification

- `tests/test_activation.py` (11) and `tests/test_plugin_api.py` (+5): decay, floor, future
  servings, recency over repetition, move narrowing, real-moment frames, empty inputs, the no-text
  rule, the strip and GIF, the named failure — and on the desktop path: stills served and served
  back as JPEG, the route refusing anything it did not write, no stills without a state, stills
  written for a state with servings, and none when nothing is firing.
- Real render: 10 frames of the live session, viewed — every frame carries activity and the arc
  fades, after two rejected attempts (all-empty early frames; then a first frame that lit
  everything).
- `tools/e2e_activation.py` — the route over **real HTTP** against a copy of the real ledger:
  three stills served, the first returned as 185,313 bytes of `image/jpeg` with a JPEG signature,
  both traversal probes refused with 404, and a chat that does not own the state served none.
- Suite: **903 passed, 1 skipped**; `spec_audit` 0 drift.

## Must not change

The wordless card, the dose-based endings, the rule that no state depends on this module, and the
fact that an activation is derived — never written back.
