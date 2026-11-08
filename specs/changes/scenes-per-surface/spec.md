# Spec change: scenes-per-surface

Status: **partial 2026-11-08** — the pane half exists (per-state motion, still frames
in chat), the per-surface grading, clock, dual scoring and 4:5 postcards do not.
Kind: rendering contract. No change to state semantics, tool policy, or the
timer.

## Goal

A state looks different depending on where the person is standing. The terminal
is a place you are inside with time passing; a chat window is a postcard that
arrives twice. Today both get the same picture at the same moment in the same
format, which is why neither feels right.

Concretely: the same state must produce a *continuous, graded, moving* view in
the terminal takeover, and a *still, well-framed, caption-free* image on chat
surfaces — and neither may show words.

## Non-goals

- No new states, no change to what material a state pulls.
- No model calls on the rendering path. Rendering must stay a pure function of
  the state dict plus the clock.
- No animation in chat: chat cannot post-and-edit, so motion is out of scope
  there by construction, not by preference.
- No video, no GIF, no sixel/kitty/iTerm image protocols (Discord must keep
  working from the same code path).

## Requirements

**R1 — motion is per state, not global.** Each state declares `hold`, `fade`,
and a `motion` kind. Contemplative states dissolve; doomscroll cuts and pushes.
A single global `HOLD_S`/`FADE_S` is removed.

**R2 — the terminal shows the clock.** A state's progress (`elapsed/total`)
drives a deterministic global grade over the frame bank — exposure, colour
temperature, and a fog/veil amount — so minute 1 and minute 11 of a walk are
visibly different places. The grade is applied after decode, never by
re-rendering.

**R3 — frames are scored twice, per target.** Terminal score is measured *after*
downsampling to the surface's pixel grid (100×52): luminance band count and
subject mass. Chat score is measured at full size. Selection uses the score for
the surface it is being shown on.

**R4 — chat gets postcards, not a feed.** An image-capable chat surface receives
one image on entry and one at resolution. States longer than 15 minutes get one
midpoint image; nothing else. An explicit `state(action="image")` still returns
a frame on demand.

**R5 — aspect follows the surface.** One render per state, two crops: 2:1 for the
terminal grid, 4:5 for chat. Chat never receives the wide strip.

**R6 — no words, anywhere.** Terminal keeps its no-`[A-Za-z]{2,}` invariant. The
chat postcard carries no caption, no title, no counter — the image is the whole
message.

**R7 — idle renders nothing.** No active state means no image on any surface.

**R8 — one place at a time.** The frame shown on any surface is derived from the
same elapsed-time index, so two windows on the same state agree.

**R9 — the origin is the destination.** Everything an action produces — the
moving frame, the postcard, the return report — is returned on the response to
the turn or command that started it, and the plugin never chooses a destination
of its own. No home channel, no background send, no second surface. A state
entered in a chat answers in that chat; a state entered in a terminal renders in
that terminal; a state entered inside a project writes its artifacts under that
project.

**R10 — nothing outlives its conversation silently.** A midpoint postcard is
delivered only on a later turn of the *same* session, identified by the
`session_id` captured at entry. If that session never speaks again, the postcard
is dropped rather than routed elsewhere.

## Acceptance criteria

1. Entering walk and rendering at t=0 and t=0.9×duration on the terminal yields
   visibly different grades (mean luminance differs by ≥ 12/255), with no word
   characters on screen.
2. Doomscroll's terminal view cuts at least once per 10 s and never dissolves;
   walk dissolves only at frame boundaries.
3. The same state's chat postcard is 4:5 and contains no text characters when
   transcribed; the terminal frame for the same instant is 2:1.
4. Entering a 30-minute dream posts exactly 3 images over its life; a 3-minute
   daydream posts 2.
5. With no active state, terminal and chat both render nothing.
6. Frame choice is stable: the same (state, elapsed) yields the same frame index
   across processes.
7. Entering a state in one chat and finishing it produces no output in any
   other chat: the report and postcard appear only in the originating session.
8. A pending midpoint postcard recorded under session A is not delivered to
   session B, and expires when A ends.

## Affected paths

- `core/realimagery.py` — motion profiles, progress grade, per-target scoring
- `core/surfaces.py` — `postcard()`, aspect crop, removal of ASCII art from
  image-capable profiles
- `core/tui.py` — stop drawing the old ASCII bank when photographs exist
- `tools/gen_frames.py` — square-crop companion output, score sidecar
- `tests/test_realimagery.py` — new
- `tests/test_surfaces.py` — postcard cases

## Must not change

- `definitions.STATES` durations, cadences, and residue strings.
- `CONTROL_TOOLS`, `/snap`, and the two-turn report decay.
- The no-model-call rule for state entry, exit, and expiry.
- `tools/term_scene.cjs` — it stays as the fallback when no photographs exist.

## Open question carried over

`specs/changes/state-return-report/spec.md` ends with an unresolved question:
should a walk's return account name the *relations* it moved along (`hypernym`,
`antonym`), not just the destinations? This change resolves it as **yes**, and
schedules it as its own task rather than folding it into the rendering work.
