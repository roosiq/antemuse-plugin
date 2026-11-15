# Design audit — panes, chat, docs

DESIGN AUDIT RESULTS

Overall assessment: the instrument idea is strong and consistently executed — a dark, quiet
glass with one accent doing all the signalling — but the cockpit's instruments do not survive a
narrow viewport, its failure language is a second language, and the map pane keeps its
interactions secret. Nothing here is a redesign; it is finishing.

Method: `design-audit` skill (installed from the community hub), whose protocol is read the
system docs → walk every screen → audit 15 dimensions → reduction filter → phased plan.
Screens walked: cockpit at 1440×900, 768×1024 and 390×844 (real Chromium, shipped
`desktop/plugin.js`, synthetic 420-node payload); the map pane from the shipped screenshot plus
its drawing code; chat, settings and docs from their text. The design system, app flow and
lessons files this audit depends on did not exist and were written first:
`docs/design/{DESIGN_SYSTEM,APP_FLOW,LESSONS}.md`.

────────────────────────────────────────────

PHASE 1 — Critical

- **Cockpit HUD @ narrow widths**: eight fixed cells are squeezed into 330px, so labels run
  into each other and the last value is cut — measured at 390×844: `PITCHROLL`, `NEAR PICK`,
  `EDGE LIT`, and `39/4.` clipped → render a **priority set** by width: `HDG SPD PICK EDGE`
  under 640px, `+ ROLL NEAR` under 900px, all eight above; enforce a minimum cell width
  (`cellW >= 56`) and wrap to a second row rather than compressing → *a person on a laptop with
  a narrow pane currently cannot read the two numbers that matter (picks and distance to the
  wall), and a clipped value reads as a broken instrument.*
- **Cockpit failure copy is raw**: `map unavailable · <err.message>` prints whatever the fetch
  threw, while the pane has five honest strings (`sign-in required`, `the plugin backend is
  not mounted`, `the backend did not answer`, `backend unavailable`, `reconnecting`) → route the
  cockpit through the same `whyFailed()` → *the same failure currently speaks two languages, and
  the technical one sends the person looking at the server instead of at their session.*
- **Reduced motion is half-implemented**: the net honours it, the tube's idle drift and the
  bullet travel do not, and the media query is read twice (once via `reducedMotion(win)`, once
  inline at mount) → gate drift and bullet travel on the same helper → *a person who asked the
  OS for less motion still gets a drifting starfield and travelling projectiles.*
- **The map pane's controls are undiscoverable**: drag-to-orbit, wheel-to-zoom, hover-to-read,
  click-to-pin and `f`-to-fit all work, and the only place they are written down is the
  canvas's `aria-label` → show a one-line hint in the instrument corner on first mount, fading
  after the first pointerdown → *a surface whose interactions are only in an accessibility
  attribute is a surface most people will drag once and abandon.*
- **No legend anywhere**: accent means firing/picked, size means ledger weight, and neither is
  stated on either surface → one line in the pane corner (`gold — firing · size — weight`) and
  the same rule stated once in the cockpit's pick panel → *the map is beautiful and unreadable:
  a person cannot tell what the colour they are looking at means.*

Review: these four are the ones where the interface is not merely unfinished but actively
misleading — a clipped number, a wrong diagnosis, a broken accessibility promise, and an
instrument with no key.

────────────────────────────────────────────

PHASE 2 — Refinement

- **HUD type hierarchy**: label 13px and value 18px at wide viewports is a 72% ratio, and both
  shrink together at narrow ones → labels fixed at 10–11px, values `clamp(15, w/105, 18)`,
  labels in `dim`, values in `text` → *the label should never be able to argue with its value.*
- **Two brand marks compete with the tape**: `Ψ ANTEMUSE` and `CONCEPT COCKPIT` both sit at the
  top, beside the heading tape that is the only thing up there worth reading → keep the wordmark,
  drop the meta label (the nav row and the route already name the surface) → *chrome that names
  the product inside the product is the first thing the reduction filter removes.*
- **Cockpit labels have no cap**: the map pane deliberately labels only the firing set; the
  cockpit labels whatever is near, which at 1,342 concepts is several at once with no collision
  rule → label the six nearest only, skip a label whose box overlaps one already placed →
  *unlabelled points are honest; overlapping labels are noise.*
- **The map has no focus state**: hover shows a tooltip and nothing else dims → on hover or pin,
  dim every node and edge outside the immediate neighbourhood to 35% and restore on leave →
  *the hairball is the pane's main legibility problem and focus is the cheapest fix for it.*
- **Spacing and tracking drift**: corner insets are 10, 12 and 18px across the two panes;
  tracking uses 0.14, 0.18, 0.24 and 0.3em with no rule → adopt the 4px scale and three tracking
  steps (`0.14em` UI, `0.24em` instrument labels, `0.3em` wordmark) → *inconsistency at this
  scale is what separates "designed" from "drawn".*

Review: none of these hurt comprehension the way Phase 1 does, but each one is the difference
between an instrument and a sketch.

────────────────────────────────────────────

PHASE 3 — Polish

- **Cockpit empty state**: with no map it draws `…` and nothing else → `no map yet · /walk
  lights concepts`, the pane's existing sentence → *an empty instrument should teach the first
  action, not indicate a spinner forever.*
- **Hit feedback**: a four-fragment burst exists; add a 300ms accent ring on the picked node and
  a single pulse of the `PICK` cell → *the shot already travels; the hit should land somewhere
  visible.*
- **Wall cue**: correct and readable, but it appears instantly → fade over 120ms → *motion at
  the boundary should feel like arrival.*
- **Focus ring**: the glass is focusable and has an aria-label but shows nothing when focused →
  1px accent at 24% inside the frame while focus is within → *keyboard users currently cannot
  tell whether their keys will fly the ship.*
- **Light theme**: unmeasured; the chains have fallbacks but contrast of `dim` on a light
  `--ui-panel-background` is unknown → measure and, if needed, raise `dim` to `--muted-foreground`
  first → *the pane claims to wear the app's theme; that claim is only tested in the dark.*
- **Bullet dot**: 4px on the canvas at dpr 1 is a 2px dot → clamp to `max(2.5, 4/dpr)` → *the
  one element that carries the whole shooting interaction should not round to nothing.*

Review: these are felt only after the first two phases, and they are cheap.

────────────────────────────────────────────

DESIGN_SYSTEM UPDATES REQUIRED

- Type scale: `label-sm 10`, `label 11`, `value 15`, `value-lg 18`, with the rule *label ≤ 70%
  of value*.
- Space scale: `4 / 8 / 12 / 16 / 24 / 32` (currently ad-hoc 7, 9, 10, 12, 18).
- Tracking: `ui 0.14em`, `instrument 0.24em`, `wordmark 0.3em` — no other values.
- New component: **HUD cell** with priority (`critical | normal | detail`) and a documented
  wrap rule.
- New component: **legend line** (one row, ≤3 items, `dim` at 70%).
- New state token: `focus-ring` — `accent` at 24%, 1px.

These must be approved and added to `docs/design/DESIGN_SYSTEM.md` before implementation.

────────────────────────────────────────────

IMPLEMENTATION NOTES FOR BUILD AGENT

- `desktop/plugin.js` ~3265 (`const cells = [...]`) and ~3273
  (`const cellW = Math.min(150, (w - 60) / cells.length)`): mark each cell
  `['HDG', value, 'critical']` etc., filter by `w`, and compute
  `cellW = Math.max(56, Math.min(150, (w - 48) / shown.length))`; if
  `shown.length * 56 > w - 48`, render a second row at `y0 + 26`.
- `desktop/plugin.js` ~3354 (`map unavailable · ${state.error}`): replace with
  `` `map unavailable · ${whyFailed(state.error)}` `` — `whyFailed` is already exported in the
  same module.
- `desktop/plugin.js` ~2442: delete the inline `matchMedia` block and call `reducedMotion(win)`
  (defined at ~1572). Gate the idle drift at ~778 (`if (!reduced) yaw += …`) and set
  `BULLET_SPEED` travel to a single-frame resolve when `reduced`.
- `desktop/plugin.js` ~968: keep the aria-label and add a DOM hint element
  (`position:absolute; left:12px; bottom:calc(HUD + 12px)`) with
  `drag to orbit · wheel to zoom · click to pin · f to fit`, opacity 0.5, removed on the first
  `pointerdown` on the canvas.
- `desktop/plugin.js` pane corner (~1449): add a legend line under `vm.counts`:
  `gold — firing · size — weight`, 10px, `dim`, only when `frame.lit > 0`.
- Cockpit label pass (in the label loop near the label placement code): sort by distance,
  `slice(0, 6)`, and skip any label whose measured rect intersects one already placed.
- Map pane hover (hover handler near ~920): on `hovered`, set a module-level `focus = label`,
  and in the node draw pass multiply alpha by `0.35` for nodes not equal to `focus` and not
  adjacent to it.
- Focus ring: draw a 1px `accent`-at-24% inset rectangle in `drawTube` when
  `doc.activeElement === el`.

Outside design scope, flagged for the build agent: `/explore <concept>` seeding, pick
injection, and the lane handoffs from `specs/changes/machine-and-person/` are functional
changes and were not designed here.

────────────────────────────────────────────

Evidence caveats

- Cockpit screenshots use a synthetic 420-node payload, so labels read `concept-101`, not real
  concept names. Label *density* findings hold; label *content* findings do not.
- The map pane was audited from the shipped screenshot `docs/screenshots/pane-walk.png` and its
  code, not from a live window: the desktop app was not running.
- Viewport tests rendered the pane at true viewport size (the harness's own box is a fixed
  900×560, which produced a false overflow reading on a first pass — 900px document width at a
  390px viewport — that was not real).
