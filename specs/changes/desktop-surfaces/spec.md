# Desktop surfaces — the state seen, not described

Status: **proposed** 2026-11-08. Not implemented. Written from a source review of a
shipped plugin, not from a sketch.
Owner: Ryan Cook. Scope: `/home/ryan/antemuse-plugin` desktop surface only.

## 1. Problem

Antemuse has no desktop surface. Everything a person sees is produced either as a
Pillow PNG attached to a chat message or as text in the CLI. Both are snapshots of a
turn: they cannot show a state *while it is running*, and neither can show the
remaining minutes counting down without spending a message.

The desktop app is the one place where a state could be visible continuously, and it
is also the one place where BR-5 becomes free rather than defended: a glyph scene
cannot leak candidate text, so "the person sees pictures, never candidates" holds by
construction on that surface instead of by assertion.

## 2. Prior art, measured (not recalled)

`dudicslevente/hermes-ascii-worlds` @ `ba8faab`, MIT. Reviewed 2026-11-08 from the
listing and the source.

- One generated file: `desktop/plugin.js`, **306 KB / 8,165 lines**, emitted by a
  dependency-free bundler. React appears only at the SDK boundary; every scene module
  is plain ESM.
- 20 habitats, each a **pure function of (canvas size, time)** painted into a hidden
  canvas at two samples per cell; a sampler then picks a glyph and a colour per cell
  with a **stable per-cell hash so glyphs do not flicker**. Nothing is a pre-rendered
  image.
- Explicit bounds: 1800×1400 logical px, DPR ≤ 2, ~4M backing pixels, 220×150 glyph
  grid, per-habitat population caps. Battery saver is 12 fps instead of 30.
- Storage: `settings.v3` (one record per habitat), `background.v1`, plus read-only
  `v2`/`v1` records for migration. Values are clamped on every read; the theme is
  never stored because the art follows the app.
- It registers a **settings page**, not a pane, and says why in the source: *"closing
  a plugin's only pane would disable the plugin."*
- `TITLEBAR_AREAS.right` contribution for the toggle, `PALETTE_AREA` commands for
  toggle and "open settings" (`pluginSettingsHref(id)`), all guarded — when the host
  lacks those surfaces the settings page still works.
- `ctx.onDispose` removes every canvas, observer, frame, style and attribute; cleanup
  does not depend on React timing.
- The optional window background is a fixed, clipped, `aria-hidden`,
  `pointer-events: none` layer with its own strength (default 28%).

Adopted from it: the settings-page-not-pane rule, the guarded-export discipline, the
dispose-everything contract, the two-samples-per-cell glyph sampler, and the
wordless-overlay approach. **Not** adopted: its 20 habitats, its bundler, and its
per-habitat colour system — Antemuse's scenes are already defined by its own states.

## 3. Proposal

Three surfaces, in order of value:

1. **State pane** (`area: 'panes'`, `placement: 'right'`): state name, minutes and
   turns left, the tool list with disallowed tools greyed, and one static glyph frame
   for the current state. Wordless apart from the strip's counts.
2. **Ambient background while a state runs**: the same scene at low strength, dim and
   click-through — "the frame is elsewhere" made visible. Off by default.
3. **Per-state settings page**: glyph density, size, palette, speed, per state —
   mirroring the per-habitat record, stored under `antemuse.v1` in `ctx.storage`.

### Data path

The desktop plugin cannot read `~/.hermes/plugin-data/antemuse/state.json`. Antemuse
must ship a small Python backend:

- `dashboard/plugin_api.py`, declared as `"api": "plugin_api.py"` in the manifest,
  serving `GET /api/plugins/antemuse/state` → `{state, ends_at, turns_left,
  tools_allowed, tools_blocked, scene}`. Counts and identifiers only; no candidate
  text, no goals.
- The desktop side polls `ctx.rest('/state')` on an interval of a few seconds.
  `ctx.socket('/events')` may be an accelerator but **not the floor**: it is a no-op
  on OAuth remotes.
- The backend is imported only when `antemuse` is in `plugins.enabled`
  (`~/.hermes/config.yaml`); it already is. This must be documented, because a
  desktop pane that silently shows nothing looks like a bug.

### Constraints inherited from the existing contract

- Rendering is inference-free. No model call may sit on the path from state change to
  pixels, exactly as entry, exit, expiry and tool restoration are inference-free.
- No candidate text, goal text or source text may reach the desktop surface. The
  endpoint returns identifiers and counts; a test must assert the response shape.
- The pane must not become the plugin's only surface: if the pane is the only
  contribution and the user closes it, the plugin disables itself.

## 4. The decision this forces

Antemuse would then have **four renderers of the same scenes**: the Pillow chat card,
the CLI text renderer, the proposed Python `scene3d`, and now JavaScript glyphs. There
is already an open question (§17.1) about whether `scene.html` or Python owns the
scene definition.

Options:

- **A — Scene as data.** One frozen scene description (glyph grid + palette + timing
  keyframes) that every renderer samples. One shared fixture all four must reproduce.
  Highest up-front cost; the only option where drift is detectable rather than
  discovered.
- **B — JS is desktop-only authority.** Desktop renders its own scenes; Python keeps
  the chat card. Cheap now, guarantees the two disagree, and nobody notices because
  each looks fine alone.
- **C — No desktop renderer.** Desktop shows the strip and a static card PNG only.
  Smallest surface, no sampler, no drift — but the pane is then a status chip, not a
  state.

Recommendation: **A**, with the fixture landing before any of the three surfaces is
built. This is an owner decision and is not assumed below.

## 5. Acceptance (when implemented)

1. `GET /api/plugins/antemuse/state` returns counts and identifiers only; a test
   asserts no goal, candidate, source or journal text appears in the payload.
2. The pane renders with `pytest tests/ -q` green, doctor unchanged in tool and hook
   counts, and no desktop-related hook added to the Python plugin.
3. With `antemuse` removed from `plugins.enabled`, the pane shows a named "backend
   unavailable" state rather than an empty box.
4. Closing the pane does not disable the plugin (no single-pane dependency).
5. Disabling the plugin removes the pane, the background layer, its style element and
   its attributes; no animation frame survives disposal.
6. Reduced motion and a paused state both render a static frame; no clocks advance
   while the canvas is hidden.
7. The same fixture reproduces identically in the Python renderer and the JS sampler
   at the same grid size — this is the anti-drift test, and it is the reason A exists.
8. No network access beyond the plugin's own backend route; no new Python dependency.

## 6. Non-goals

- No new agent tools, hooks or LLM calls. The desktop surface reads state; it never
  changes it.
- No scenes beyond the four states.
- No desktop-side creativity claims, scoring, or candidate display of any kind.
- Not a replacement for the chat card until the fixture test exists.

## 7. Open decisions (owner)

1. Scene source of truth: A, B or C in §4.
2. Is an ambient background acceptable at all, given it sits behind text? If yes, what
   strength ceiling?
3. Does the desktop pane replace the chat card for desktop users, or coexist?

## 8. Verification limitation, stated plainly

The Hermes desktop app is **not installed on this machine** — there is no
`~/.hermes/desktop-plugins/` — so none of this can be built and tested here. The
specification is written from the SDK surface and from a shipped plugin's source; the
implementation must be verified on a machine that runs the app, and until then this
change stays `proposed`.
