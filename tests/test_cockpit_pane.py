"""The cockpit pane, as the host will load it.

The desktop half is one uncompiled ES module: there is no bundler to catch a
missing import, a hardcoded colour, or a listener that never comes off. These
tests read the shipped file and hold the cockpit to the same rules the rest of
the pane follows — theme colours only, the one `/graph` route as its source, a
canvas that tracks its box, and a destroy that actually releases everything.

The rendering itself is verified in a browser by `tools/cockpit_harness.py`,
which imports this exact file with the SDK stubbed and drives the export.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "desktop" / "plugin.js"


def cockpit_block() -> str:
    js = PLUGIN.read_text()
    start = js.index("// ---------------------------------------------------------------- the cockpit")
    end = js.index("// Kept as a named export so a harness")
    return js[start:end]


def test_the_status_chip_carries_the_dose_not_only_a_label():
    """The status bar is the only ambient surface; a state half spent must show it there."""
    js = PLUGIN.read_text()
    assert re.search(r"export function chip\(payload\)", js), "no chip() to derive the readout"
    assert "active.dose" in js and "active.unit" in js
    assert "[vm.label, dose].filter(Boolean).join(' · ')" in js, \
        "the chip label is not built from the state and its dose"
    # an open-ended state has no dose to promise, and says what it has instead
    assert "picked" in js


def test_the_cockpit_is_a_tab_inside_antemuse():
    """One plugin is one product: the cockpit is a tab beside the state, not a second nav row.

    It used to register its own full-height pane and its own sidebar entry, which put two
    things called Antemuse in the sidebar and made a person choose before they could compare.
    """
    js = PLUGIN.read_text()

    assert "function AntemuseScreen(" in js, "the page that holds both tabs is gone"
    assert js.count("area: SIDEBAR_NAV_AREA") == 1, "the cockpit got its own sidebar row back"
    assert "id: 'cockpit-nav'," not in js
    assert js.count("area: PANES_AREA") == 1, "the cockpit registered its own full-height pane again"
    for needle in (
        "id: 'cockpit-page',",
        "id: 'cockpit-open',",
        "path: `/${ID}/cockpit`",
        "render: () => jsx(AntemuseScreen, { ctx, start: 'cockpit' })",
        "render: () => jsx(AntemuseScreen, { ctx, start: 'state' })",
    ):
        assert needle in js, f"the cockpit registration lost {needle!r}"


def test_the_page_shows_both_tabs_and_a_tab_is_a_button():
    js = PLUGIN.read_text()
    block = js[js.index("function AntemuseScreen("):]
    block = block[:block.index("\n}\n")]

    assert "copy.state" in block and "copy.cockpit" in block
    assert "role: 'tab'" in block and "'aria-selected'" in block
    assert "setTab(" in block, "a tab that cannot be chosen is a label"
    # theme variables only: a tab strip is chrome, not a colour scheme
    assert "#" not in block.replace("#fff", ""), "a literal colour in the tab strip"


def test_the_cockpit_reads_the_one_graph_route_and_invents_no_positions():
    """A second surface for the same map must read the same numbers.

    If this file ever re-projects coordinates, or falls back to random jitter
    when a node has no stored position, the cockpit and the pane would disagree
    about where a concept is — which is the one thing the shared route prevents.
    """
    block = cockpit_block()
    assert "'/graph?limit=" in block, "the cockpit must ask the graph route for the map"
    assert "/state" not in block, "the cockpit draws the map, not the state envelope"
    assert "Math.random" not in block, "positions come from the payload, never from chance"
    assert "Number.isFinite(n.x)" in block, "a node without a real projection must be dropped"


def test_the_cockpit_takes_its_colours_from_the_app_theme():
    """The pane is inside the desktop, so it wears the desktop's colours.

    Two passes got this wrong before: a Nous palette, then a phosphor-green one.
    Both painted their own surface and looked like a foreign app in the window.
    Now the theme is read from the host's CSS variables at mount, and the only
    literals left describe the tube itself — a black raster and a black vignette,
    which are hardware, not brand.
    """
    js = PLUGIN.read_text()
    block = cockpit_block()
    start = block.index("function cockpitTheme(")
    body = block[start:block.index("\n}\n", start)]
    assert "getComputedStyle" in body, "the theme must be read from the host"
    for var in ("--ui-accent", "--ui-panel-background", "--ui-text"):
        assert var in js, f"the cockpit does not read {var}"

    # No hue may be written here: only neutral greys (the tube, and the
    # no-theme fallback) are allowed as literals.
    def neutral(lit: str) -> bool:
        if "$" in lit or lit in ("rgb()", "rgba()"):
            return True                      # code, not a value
        hexm = re.fullmatch(r"#([0-9a-fA-F]{3,8})", lit)
        if hexm:
            h = hexm.group(1)
            if len(h) in (3, 4):
                return h[0].lower() == h[1].lower() == h[2].lower()
            return h[0:2].lower() == h[2:4].lower() == h[4:6].lower()
        nums = re.findall(r"-?[\d.]+", lit)
        return len(nums) >= 3 and nums[0] == nums[1] == nums[2]

    hits = set()
    for pattern in (r"#[0-9a-fA-F]{3,8}\b", r"\brgba?\([^)]*\)"):
        hits.update(m.group(0) for m in re.finditer(pattern, block))
    stray = {h for h in hits if not neutral(h)}
    assert not stray, f"a hue outside the app theme: {sorted(stray)[:4]}"

    # DOM chrome asks the app for its variables instead of naming colours
    assert "var(--ui-panel-background" in block, "panels must use the app's panel colour"
    assert "var(--ui-accent" in block, "interest must use the app's accent"


def test_alpha_is_derived_from_a_theme_colour_not_guessed():
    """A var() is a colour, not a string you can append '55' to."""
    block = cockpit_block()
    assert "function withAlpha(" in block, "no alpha helper"
    assert "parseInt(" in block and "rgba(" in block, "the helper must parse hex and rgb()"


def test_the_theme_names_every_colour_the_drawing_asks_for():
    """An undefined token is silent: canvas keeps the last strokeStyle.

    `theme.paper` was missing while shots asked for it, so tracers inherited
    whatever colour was set last and came out yellow. Nothing threw. So: every
    `theme.*` reference in the block must exist in the object cockpitTheme
    returns.
    """
    block = cockpit_block()
    used = set(re.findall(r"theme\.([a-zA-Z]+)", block))
    start = block.index("function cockpitTheme(")
    body = block[start:block.index("\n}\n", start)]
    defined = set(re.findall(r"^\s{4}(\w+):", body, re.M))
    missing = used - defined
    assert not missing, f"the drawing asks for colours the theme never sets: {sorted(missing)}"


def test_the_type_is_crisp_and_named():
    """Retro is the tube, not a coarse raster.

    The cockpit sits on a phosphor monitor, so it gets green, bloom, scanlines
    and a vignette — but the glyphs are drawn at full resolution. An earlier pass
    downsampled the type to look like a character ROM; that was pixel art, not a
    vector display, and it made the readouts worse. Guard the recovery.
    """
    js = PLUGIN.read_text()
    assert "const FONT = {" in js
    for role in ("display", "label", "data"):
        assert re.search(rf"^\s*{role}:", js, re.M), f"the type system lost the {role} role"
    block = cockpit_block()
    assert "pixelText(" not in block, "type must not be downsampled: a vector display is sharp"
    assert "imageSmoothingEnabled = false" not in block, "no nearest-neighbour blit of the world"
    for m in re.finditer(r"c2d\.font = ", block):
        tail = block[m.end():m.end() + 80]
        assert "FONT." in tail, f"inline font instead of a role: {tail.splitlines()[0]!r}"


def test_the_wordmark_appears_once_and_is_the_mark_plus_the_name():
    block = cockpit_block()
    assert "String.fromCodePoint(0x3A8)" in block, "the mark is PSI"
    assert "antemuse" in block and "CONCEPT COCKPIT" in block
    assert block.count("fillText('ANTEMUSE'") == 1, "one wordmark, not a watermark"


def test_the_canvas_tracks_its_box_instead_of_a_mount_size():
    """Panes resize constantly: sash drags, layout switches, tab moves.

    Two failures this guards: sizing the canvas once at mount, and measuring the
    canvas element itself — whose CSS size follows its own width attribute, so
    the two feed back into each other and the backing store runs away.
    """
    block = cockpit_block()
    assert "ResizeObserver" in block
    assert "el.width = Math.max(1, Math.round(w * view.dpr))" in block
    assert "el.height = Math.max(1, Math.round(h * view.dpr))" in block
    assert "el.parentElement" in block, "measure the pane box, not the canvas"


def test_destroy_releases_every_listener_and_timer():
    block = cockpit_block()
    adds = re.findall(r"el\.addEventListener\('(\w+)'", block)
    removes = re.findall(r"el\.removeEventListener\('(\w+)'", block)
    assert sorted(adds) == sorted(removes), f"unbalanced listeners: {adds} vs {removes}"
    assert "stopPoll" in block and "cancelAnimationFrame" in block
    assert "ro.disconnect()" in block, "the ResizeObserver must come off"


def test_the_cockpit_flies_like_a_ship_not_a_camera():
    """Panning a camera and flying a ship are different motions.

    A ship banks, spools its throttle and keeps its momentum when the throttle
    is cut. Those three are what the eye reads as flight, so they are pinned
    here: roll inside the camera basis, a velocity vector bled by drag, and a
    throttle that eases rather than snapping to full.
    """
    block = cockpit_block()
    assert "state.cam.roll" in block and "* cr +" in block, "roll must reach the camera basis"
    assert "state.cam.vx +=" in block and "Math.exp(-dt" in block, "thrust must build a velocity"
    assert "state.cam.x += state.cam.vx * dt" in block, "position must integrate the velocity"
    assert "Math.min(1, dt * 3.2)" in block, "the throttle must spool"


def test_the_mouse_can_be_captured_and_released():
    """Click-to-fly needs the pointer; a pane that seizes it and never yields traps the app."""
    block = cockpit_block()
    assert "requestPointerLock" in block
    assert "pointerlockchange" in block
    assert "exitPointerLock" in block, "destroy and Escape must both hand the pointer back"
    assert "movementX" in block, "a captured pointer steers by relative movement"


def test_shooting_is_a_stream_of_travelling_bullets():
    """Asteroids, not a sniper rifle: hold to fire, and the shots have to arrive.

    A hitscan pick would report a hit the instant you pressed the button, which
    is selection wearing a gun. Bullets are objects with a position and a life,
    collision happens in world space, and a miss is a shot that expires.
    """
    block = cockpit_block()
    assert "function shootAt(" in block, "there is no shot"
    assert "BULLET_SPEED" in block and "BULLET_LIFE" in block, "shots must travel and expire"
    assert "function stepBullets(" in block, "nothing advances the shots"
    assert "state.firing && state.cool <= 0" in block, "holding the trigger must keep firing"
    assert "FIRE_INTERVAL" in block, "fire rate must be a rate, not a click"
    assert "state.hits[hitNode.l] = (state.hits[hitNode.l] || 0) + 1" in block, \
        "an arriving shot must raise that concept's interest"
    assert "z.hits - a.hits" in block, "the pick list must be ordered by interest"
    assert "onPicks(pickList())" in block, "the pane must hear about a pick"
    assert "'f'" in block, "the keyboard needs a fire key"


def test_nothing_can_be_selected_only_shot():
    """The interaction is the shot. A lock step would put a cursor back in it."""
    block = cockpit_block()
    assert "function lockAt(" not in block, "no select step: the shot is the interaction"
    assert "children: 'locked'" not in block, "the pane must not carry a locked chip"
    assert "state.firing = false" in block, "the trigger has to release"


def test_the_net_opens_where_the_ray_is_densest():
    """A fixed-distance net reports empty space in a cloud full of gaps.

    The sweep is what makes a throw land on structure; the fallback is what
    makes a throw into a gap still land on the nearest thing ahead.
    """
    block = cockpit_block()
    assert "countAt" in block and "for (let d = 0.3; d <= 2.4; d += 0.1)" in block
    assert "bestAngle" in block, "the empty-cone fallback must exist"


def test_the_edge_is_a_wall_that_stops_the_ship():
    """Hitting the boundary has to stop the ship, not spring it back.

    A radial spring reached equilibrium with the throttle, so holding W pinned
    the ship at the boundary at walking speed for as long as you held it, and a
    purely radial correction let it slide along the shell. The wall clamps the
    position and kills the velocity instead.
    """
    block = cockpit_block()
    assert "state.cam.x = nx * MAP_RADIUS" in block, "the position is not clamped to the edge"
    assert "state.cam.vx = 0" in block, "contact does not stop the ship"
    # Cancelling only the outward component left the ship creeping along the shell; the
    # stop is unconditional now, so there must be no outward test guarding it.
    assert "const outward = state.cam.vx * nx" not in block, \
        "contact is conditional again — the ship can slide along the wall"
    assert "const pull = (radius - MAP_RADIUS)" not in block, (
        "the edge still springs the ship back instead of stopping it"
    )
    assert "const bound = 6" not in block, "the box bound is dead code once the wall is a sphere"


def test_an_explore_points_at_the_cockpit():
    """A state whose surface is another pane has to hand the person the door.

    `/explore` can start while the dock pane is what is on screen. Without a way in, the
    state exists and nobody flies it — the nav row is a place you have to already know about.
    """
    js = PLUGIN.read_text()
    assert "payload.active.key === 'explore'" in js, "the pane never looks at which state is running"
    assert "`/${ID}/cockpit`" in js, "no route to the cockpit from the state surface"
    assert "open the cockpit" in js, "no way in offered while exploring"


def test_the_cockpit_polls_no_faster_than_the_pane():
    block = cockpit_block()
    assert "const COCKPIT_POLL_MS = 4000" in block


def test_shots_leave_the_cannons_not_the_middle_of_the_glass():
    """The stream has to come out of the ship.

    A shot that appears at the centre of the canopy reads as the camera firing.
    Each shot starts at a visible cannon muzzle, and is aimed at whatever the
    reticle is on, so the two barrels converge instead of shooting parallel.
    """
    block = cockpit_block()
    assert "function drawCannons(" in block, "no cannons to fire from"
    assert "drawCannons()" in block, "the cannons are never drawn"
    assert "function gunScreen(" in block, "no muzzle position"
    assert "aimDir(gun.x, gun.y)" in block, "the shot does not leave the muzzle"
    assert "function aimPoint(" in block, "no convergence target"
    assert "state.kick[side < 0 ? 'l' : 'r'] = GUN_KICK" in block, "no recoil"


def test_the_cockpit_names_the_current_concept_and_records_a_verdict():
    """A pick count without its label is not intelligible or reviewable."""
    block = cockpit_block()
    assert "onName" in block, "cockpit events do not expose a named concept"
    # `hit` events deliberately remain individual: each arriving bullet should
    # refresh the readout even when it meets the concept that the last one met.
    assert "onName(hitNode.l, 'hit')" in block, "a bullet impact does not name its concept"
    assert "nameNode({ l: state.target }, 'target')" in block, "reticle focus does not name its concept"
    assert "function CockpitVerdict" in block, "there is no verdict control surface"
    assert "`/api/plugins/${ID}/verdict`" in block
    assert "{ label, verdict, session: readSession() }" in block
    assert "'/verdicts'" in block, "the verdict tally is never read"
    assert "kept ${" in block and "dropped ${" in block
    assert "'aria-keyshortcuts': key" in block
    assert "control('keep', 'K', 'keep')" in block
    assert "control('trash', 'T', 'trash')" in block
    assert "onFocus: (event) => { event.currentTarget.style.outline = '2px solid var(--ui-accent" in block, \
        "verdict controls lack visible focus"
    assert "hitNotice" in block and "`${notice.source} · ${notice.label}`" in block
    assert "const fade = reduced ? null : setTimeout" in block, "hit notice does not respect reduced motion"
    # The packaged app renders the pane on a file:// origin, where a relative fetch to
    # the gateway fails ("Failed to fetch"). Judgements must go through the host's rest
    # door, or the controls render and record nothing.
    assert "ctx.rest('/verdict', { method: 'POST', body: payload })" in block, \
        "verdicts are posted with a relative fetch that fails in the packaged app"
    assert "ctx.rest('/picks', { method: 'POST', body: payload })" in PLUGIN.read_text(), \
        "picks are posted with a relative fetch that fails in the packaged app"


def test_the_cockpit_has_a_door():
    """A first-person view with no exit is a trap: tab in, and nothing gets you out.

    Escape used to only release the pointer — so in a pane that never held one, the key did
    nothing at all, and there was no button, no key and no hint. The first version of this
    test counted `onExit()` across the whole file and passed with the Escape call deleted,
    because the button and the teardown also call it. Both checks are now scoped to the code
    they are about.
    """
    js = PLUGIN.read_text()

    # 1. the Escape branch itself must leave, not merely stop the pointer
    branch = js[js.index("k === 'escape'"):]
    branch = branch[:branch.index("const onKeyUp")]
    assert "onExit()" in branch, "Escape releases the pointer but never leaves the cockpit"
    assert "state.firing = false" in branch, "Escape leaves the trigger on"

    # 2. the drawn control is a real button wired to the same exit
    button = js[js.index("const exitButton = "):]
    button = button[:button.index("return jsxs(")]
    assert "type: 'button'" in button, "the exit is not a real control"
    assert "aria-label': 'Leave the cockpit'" in button
    assert "onClick:" in button and "onExit()" in button, "the door is drawn but not hinged"

    # 3. the idle hint names it, so the key is discoverable without clicking
    hint = js[js.index("const hint = engaged"):]
    hint = hint[:hint.index("const hitNotice")]
    assert "esc exits" in hint, "the hint line never mentions the way out"


def test_the_mouse_stays_captured_after_the_button_is_released():
    """Capture must be sticky. Steering that only worked while the button was down reads as
    "mouse capture is not working" to anyone who clicks once and then moves."""
    js = PLUGIN.read_text()

    assert "let engaged = false" in js
    capture = js[js.index("const onDown = (ev) => {"):]
    capture = capture[:capture.index("const onMove = (ev) => {")]
    assert "engaged = true" in capture, "a press never captures"
    assert "pointerNote" in capture, "a refused pointer lock leaves no evidence of why"

    move = js[js.index("const onDocMove = (ev) => {"):]
    move = move[:move.index("const onUpDoc")]
    assert "if (engaged)" in move, "steering still requires the button to be held"

    release = js[js.index("const onUp = (ev) => {"):]
    release = release[:release.index("const onLockChange = () => {")]
    assert "engaged = false" not in release, "releasing the button drops the capture"
