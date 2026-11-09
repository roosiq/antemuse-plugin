# Desktop surfaces — the state seen, not described

Status: **verified in the app** 2026-11-08. Backend route and desktop half built, then
booted inside Hermes Desktop on a virtual display: chip renders live, page renders live.
The dock pane alone did not render (see §7b). Written from a source review of a shipped
plugin, then built.
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

## 3a. Decisions taken (owner, 2026-11-08)

1. **Python owns the scenes; the desktop displays served frames.** The backend calls the
   same `surfaces.art()` the CLI calls and returns the glyph lines as text. The JS half
   renders text and samples nothing. This resolves §4 by dissolving it: there is still one
   renderer, so there is no fourth one to drift.
2. **Glyph set stays the existing luminance ramp** (`" .:-=+*#"`). Braille was considered
   and dropped: these scenes are luminance fields, and a braille canvas would be a second
   renderer with a different look — exactly what decision 1 avoids.
3. **The desktop half lives in this repository** at `desktop/plugin.js`, which the app loads
   from `$HERMES_HOME/plugins/<name>/desktop/plugin.js` — the symlinked plugin directory, so
   there is nothing extra to install.

## 4. The decision this forces (resolved by 3a.1)

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
- ~~No scenes beyond the four states.~~ **Amended 2026-11-08 (§9):** the four
  states are what the agent *enters*; the pane also paints two ambient scenes so it
  is never blank. No fifth state is added — nothing enters `idle` or `work`.
- No desktop-side creativity claims, scoring, or candidate display of any kind.
- Not a replacement for the chat card until the fixture test exists.

## 7. Open decisions (owner)

1. Scene source of truth: A, B or C in §4.
2. Is an ambient background acceptable at all, given it sits behind text? If yes, what
   strength ceiling?
3. Does the desktop pane replace the chat card for desktop users, or coexist?

## 7a. What was built and what was proven

- `dashboard/manifest.json` + `dashboard/plugin_api.py`: `GET /state` mounted at
  `/api/plugins/antemuse/`, payload from the pure `dashboard/projection.py`. Counts, names
  and glyph lines only — the state's `directive`, the goal, the journal and any candidate
  text are absent, and `tests/test_plugin_api.py` asserts that structurally (every key is
  walked) rather than by review.
- `desktop/plugin.js`: a pane (`area: 'panes'`, placement right), a status chip
  (`statusBar.right`) so a closed pane cannot disable the plugin, a palette command, and a
  settings page when the host offers one. It polls `ctx.rest('/state')` every 2 s through
  `ctx.setInterval`, and reports `backend unavailable` when the route is missing.
- Proven without the app: eight pytest tests on the projection, an HTTP end-to-end
  (`TestClient`) that enters a real state in a temporary home and reads the mounted route —
  idle → `active: null`; daydream → label, `tools.mode: none`, 179 s, 2 turns; stop → null —
  and a jsdom mount of the real plugin file asserting DOM text, the `<pre>` glyph lines,
  `aria-hidden` on the art, the poll tick, unmount, idle, and the unavailable state.
  `hermes_cli.plugin_validate_desktop` reports no findings.
- **Still unproven:** how it looks in the app. No Electron here, so CSS, pane placement and
  the real gateway transport are untested. The change stays `partial` until it is seen.

## 7b. Verified inside the app (2026-11-08)

The packaged app was already up to date, so `hermes desktop` installed the launcher
entry without a build. No compositor was live on this box (only gdm's greeter), so the
app was booted on `Xvfb :99` with `--remote-debugging-port=9222` and driven over CDP.

- The app discovered the plugin itself: `~/.hermes/desktop-plugins/antemuse/` with
  `.hermes-package.json` `{"linked": true, "source": "~/.hermes/plugins/antemuse/desktop"}`,
  and the copied `plugin.js` is byte-identical to `desktop/plugin.js`.
- Enabled through the app's own decision store (`hermes.desktop.pluginDecisions.v2`).
- **Chip: renders.** `WALKING · 2:25` in the status bar; `[data-antemuse-state]`
  reflects the live payload.
- **Pane: adopted, but not visible.** The layout tree held `antemuse:state` as an
  inactive tab beside `review` in the right rail; making it active (via the stored
  tree, and by giving it its own group) left `getBoundingClientRect()` at 0 × 0.
  A dock pane is not a dependable first surface.
- **So a route and a nav entry were added** — which is what the palette command had
  been pointing at all along (`/antemuse` did not exist). Clicking **State** in the
  sidebar renders the same view at 700 × 746 with a live `DOOMSCROLLING` state.

That measurement is also the reason for `specs/changes/immersive-visuals/spec.md`:
in a 700 × 746 pane the frame drew at ≈ 264 × 120 px, 4.4 % of the surface.

## 8. Verification limitation, stated plainly

The Hermes desktop app is **not installed on this machine** — there is no
`~/.hermes/desktop-plugins/` — so none of this can be built and tested here. The
specification is written from the SDK surface and from a shipped plugin's source; the
implementation must be verified on a machine that runs the app, and until then this
change stays `proposed`.

## 9. Ambient scenes: idle and work (owner, 2026-11-08)

### Problem

`plugin_api.state()` built glyph lines only when a state was active, and
`projection.project()` returns `active: null` between states. So outside a state
the pane painted nothing and said `no state`. Verified in the app on 2026-11-08:
the State view opened, the plugin loaded, and the main pane was empty.

An empty pane is not a neutral default. This product is a place you are *in*; a
surface that goes blank the moment the agent is at rest contradicts that, and it
also makes the pane useless as a background.

### Decision

The pane is never blank. Between states it paints one of two ambient scenes,
chosen by whether a turn is in flight:

| scene | when | trail | speed | symmetry | strands |
|---|---|---|---|---|---|
| `idle` | no active state, nothing running | 30 | 0.012 | 2-fold | 2 |
| `work` | no active state, a turn in flight | 17 | 0.046 | 4-fold | 4 |

`idle` is slower and sparser than any of the four states — it is the thing you
leave on. `work` is denser and four-fold, so a busy agent looks busy without
being loud enough to read as anxiety.

### Mechanism

- The renderer is `core/screensaver.py` — Mystify strands drawn straight into the
  ramp (` .:-=+*#`), no image, no grading, no font. `tools/screensaver.py` is a
  CLI wrapper over the same module, so the CLI, the pane and the brand proofs
  cannot drift.
- `frame(state, cols, rows, now)` advances by clock phase only, so any surface
  asking at any moment gets a consistent picture without holding a loop.
- `GET /api/plugins/antemuse/state?busy=1` selects `work`; the default is `idle`.
  `busy` changes **only** the ambient scene — it never fabricates an active state
  or touches the projection.
- If a state is active, its own scene renders exactly as before; the ambient
  scenes are a fallback, not a replacement.

### Acceptance

9. With no active state, `GET /state` returns non-empty `art` for the requested
   grid, and the payload still contains no goal, candidate, source or journal text.
10. `busy=1` changes the scene and nothing else: `active` stays `null` and every
    other field is byte-identical to the non-busy response.
11. `core/screensaver.frame()` is deterministic for a given `now`, and returns
    exactly `rows` lines of exactly `cols` cells.
12. The ambient scenes render at 116×74 (pane geometry) with ink between 2% and
    8% — visible, not a smear. Measured 2026-11-08: idle 3.7%, work 4.2%.
13. No new Python dependency; the renderer is stdlib only.

### Open

- Whether `busy` should come from the gateway event stream rather than a query
  parameter the pane sets. Today the pane decides; that is a stub, not a contract.
- Whether `idle` deserves its own entry in the state vocabulary the user can
  choose, or stays purely automatic. Recommendation: automatic only.

## 10. Why the state is in a pane (owner question, 2026-11-08)

**Asked:** why does the state render in a side panel rather than in the background
of the chat it is effective on?

**Answer, from the shell's own source, not from preference.** The desktop app gives
plugins these areas (`apps/desktop/src/sdk/areas.ts`): `panes`, `statusBar.left|right`,
`titleBar.*`, plus routes, sidebar nav, palette commands and a settings page. There is
no chat-background area. The chat's own backdrop exists — `apps/desktop/src/store/backdrop.ts`
— but it is a **boolean that toggles a fixed statue image** behind the transcript:

```ts
/** Whether the faint statue image renders behind the chat transcript. */
export const $backdrop = atom(storedBoolean(KEY, false))
```

Not a renderer, not a slot, not reachable from a plugin bundle. (The web dashboard has a
`backdrop` *slot*; the Electron app does not.) So a pane is not a design choice that beat
the background — it is the only surface the plugin SDK currently offers that holds a
picture. We shipped it there because it was the only place it would go.

**The correct surface is the chat's background**, because a state is bound to a
conversation, not to the application chrome: two chats can be in different states, and one
such state art behind all of them at once is wrong by construction.

**What it would take (host change, not a plugin change):**

1. Expose a per-conversation background area — e.g. `CHAT_BACKDROP_AREA` or a
   `chat:backdrop` slot — in `apps/desktop/src/sdk/areas.ts`, mounted inside the chat
   view behind the transcript at z-0, `pointer-events: none`, `aria-hidden`.
2. Have it receive the active conversation id so the plugin can ask the backend for the
   state that governs *that* chat rather than "the profile's state".
3. Only then retarget `desktop/plugin.js` from `PANES_AREA` to that area. Until then the
   pane stays, and it is a stub with a known wrong scope — recorded here rather than
   described as finished.

**Interim rule:** if the pane is what ships, it must never be the only way to see or keep
the state. It is not: the status chip, the route, the sidebar entry and the CLI all read
the same state, and closing the pane disables nothing.

**Blocked on:** a Hermes desktop-shell change. Not attempted here: editing the shell to
add an area is a host change with its own review, and this spec governs the plugin.
