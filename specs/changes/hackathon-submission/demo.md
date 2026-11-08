# Demo — production plan

Status: planning 2026-11-08. Nothing recorded yet.
Artifact: one public X post, video **strictly under 90 seconds**, showing the
plugin working, tagging `@NousResearch`. Target: **80 s, 1280×720, H.264 MP4**.

Companion to [`plan.md`](plan.md) W4. Task ids H40–H45 in [`tasks.md`](tasks.md).

## 1. The one claim the video makes

> A Hermes state is not a mood in a prompt. The host enforces it: tools stop
> working, the reply changes shape, the person sees a picture, and when it ends
> the agent comes back with an account and keeps working.

Everything in the cut serves that sentence. The video does **not** claim the
agent gets more creative — `docs/spec.md` §16 has no evidence for it and §18
forbids the claim.

## 2. Viewing conditions drive the design

- Watched on a phone, muted, at ~390 px wide. Therefore: **burned-in captions**,
  large type, one idea per shot, no voiceover, no cursor-hunting.
- X autoplays silently, so sound is optional; if added, it must not carry meaning.
- Terminal text on a phone is the main legibility risk. Mitigation: 18–20 px mono,
  dark background, ≤ 100 columns, and captions that state the point so the
  terminal text is evidence rather than the message.

## 3. Story beats and shot list (80 s)

State used in the video: **daydream**, entered from the `state` tool with
`block: true`. That detail is load-bearing: since the `non-blocking-states`
change, states are **open by default** — `/daydream` alone does not close
anything, and `allow:` is refused without `block: true`. The refusal only exists
when the entry asks for it, and showing the host enforce an explicit request is
both truthful and the stronger beat.

Exact strings below were produced by the real plugin on 2026-11-08 in a temp
state home; they are the words the video must show.

| t | action on screen | the line it produces | caption |
|---|---|---|---|
| 0:00–0:06 | a real failing test scrolls to its red line | `1 failed, 3 passed` (real output) | **3 hours in. Same failing test.** |
| 0:06–0:14 | `/mood stuck` then `/break` | `break: break due (on the report alone) · 0m · 0 turn(s) · feeling stuck — walk (a different edge is more useful than another attempt)` | **The plugin watches the work — minutes, turns, failed calls.** |
| 0:14–0:24 | the request: "daydream, and close the tools" → the agent calls `state(action="enter", name="daydream", block=true)` | `DAYDREAMING · 3 min · 2 turn(s) · two memories · join only if it holds` | **A state is a contract, not a mood.** |
| 0:24–0:32 | the agent tries to run `ls` | `the agent is dreaming; no tools in this state. /return to come back.` | **Not a prompt. The tool call never runs.** |
| 0:32–0:46 | `antemuse` takeover: wordless art, live clock, key legend; hold, let it breathe | `DAYDREAMING · 2:41` + scene | **What the person sees. No words, by design.** |
| 0:46–0:58 | `/return` | `DAYDREAMING ended · daydream 1m · 2 step(s)` + `Summarise it in three lines — where it went, what it touched — then get back to work.` | **It comes back with an account.** |
| 0:58–1:08 | the next reply, carrying the marker, then the edit resumes | `— daydreaming, 2 min left · /return to come back` | **Then the work continues.** |
| 1:08–1:16 | `hermes plugins validate` output and the test tail | `16/16 checks ok · warnings: []` / `677 passed` | **16 checks green. 677 tests.** |
| 1:16–1:20 | end card | repo URL + catalog PR number | **antemuse · github.com/roosiq/antemuse-plugin** |

Nothing is speed-ramped across a failure. Cuts happen on solves and on idle waits;
if a cut hides a wait, the caption says so (`40 s later`).

## 4. Preconditions for each shot

- **Failing test** — use a real failing test in a scratch repo, not the plugin's
  suite. It must actually fail on camera and pass or be abandoned later.
- **`/break` says "break due"** — needs strain ≥ 1. The cheapest deterministic
  route is `/mood stuck` first (report weight +1.0), which is truthful for the
  scenario and prints "on the report alone".
- **Blocked tool** — the entry must pass `block: true`; `/daydream` on its own
  leaves every tool open. In the running session the agent calls
  `state(action="enter", name="daydream", block=true)`, which is visible in the
  transcript as the decision, then attempts a non-control tool (`ls` the repo)
  and the host refuses it. The `state` tool stays exempt by design; do not show
  that as a loophole.
- **Material in the account** — daydream cadence is 10 s, so give it 20 s before
  `/return`; otherwise the account honestly reads `nothing arrived` and the beat
  is weaker.
- **Validator and test tail** — run on the exact freeze commit, not the working
  tree, and show the real numbers. If the count changes before the pin, re-shoot
  this beat rather than editing the number.

## 5. Capture harness (verified working 2026-11-08)

Installed for this: `xterm`, `xdotool` (dnf). Available already: `tmux`, `Xvfb`,
`ffmpeg` 8.1.3, `ffprobe`, `Pillow`.

There is **no libx264** in `ffmpeg-free`; H.264 comes from `libopenh264` (or
`h264_vaapi`). VP9 exists but X wants MP4/H.264.

```bash
# one virtual display, one window, one recording
Xvfb :77 -screen 0 1280x720x24 &
DISPLAY=:77 xterm -fa 'Liberation Mono' -fs 18 -bw 0 -bg '#0b0b0f' -fg '#e8e8e8' \
  -geometry 118x32+0+0 -e tmux new -A -s demo &
sleep 2
xdotool mousemove 4000 4000            # keep the pointer out of frame
DISPLAY=:77 ffmpeg -f x11grab -video_size 1280x720 -framerate 30 -i :77 \
  -c:v libopenh264 -b:v 6M -pix_fmt yuv420p -movflags +faststart take.mp4
# drive the session from another shell:
tmux send-keys -t demo '/mood stuck' Enter
```

Verified today: 1280×720, 30 fps, H.264, crisp text, 3 s ≈ 37 KB. Text video is
cheap; do not downscale to save bytes.

Drive typing with `tmux send-keys` (deterministic) rather than `xdotool type`
(keycode/font races). `-bw 0` removes the window border; move the pointer off the
Xvfb screen so the I-beam never appears in frame.

## 6. Isolation and stale code — two traps found while planning

**Trap 1: the live gateway runs old code.** This planning session was interrupted
twice by `the agent is daydreaming; no tools in this state`, while the current
`core/engine.py` only blocks when the entry passes `block: true` (the
`non-blocking-states` change). The gateway process still holds the module it
loaded at startup. Consequence: never infer demo behaviour from what the live
agent does, and run every rehearsal in a **fresh** process on the pinned commit.

**Trap 2: a state entered in the live profile stops real work.** It happened to
this session mid-planning. Rehearse under a throwaway `HERMES_HOME` or a copy of
the plugin install, and prove isolation by reading the live `/state` before and
after. `ANTEMUSE_STATES_HOME` isolates the *state file*; it does not isolate the
plugin module the gateway already has in memory.

If the live agent does get caught, `state(action="exit")` is exempt from the
block; `/return` from the operator is the other way out.

## 7. Edit and encode

- Captions: burned in with `drawtext` (Liberation Mono, 34–40 px, white on
  `#000000@0.55` band), lower third, max 2 lines, ≤ 42 characters per line.
- Cuts: hard cuts only. No transitions, no zoom moves, no fake terminal glow.
- Encode: `-c:v libopenh264 -b:v 6M -pix_fmt yuv420p -movflags +faststart`,
  1280×720, 30 fps, no audio stream (or silence).
- Target: 80 s, < 12 MB. X limit is far above that; legibility is the constraint.

## 8. Acceptance for the demo artifact

- D1. `ffprobe` duration **< 90.0** and > 70.0 (no accidental truncation).
- D2. Every terminal line is reproducible by running the same commands; no
  invented output, no edited numbers.
- D3. Captions readable at 390 px wide; terminal text at least readable at 720 px.
- D4. The blocked-tool shot shows the refusal, not a description of it.
- D5. No claim of creativity improvement anywhere in the video, caption or post.
- D6. The post tags `@NousResearch`, the video plays logged out, and the repo URL
  in the end card resolves.
- D7. Ryan signs off on the phone-size watch before posting.

## 9. Risks

| risk | mitigation |
|---|---|
| A blocked state interrupts the recording session | record under an isolated profile; `state(action="exit")` as the escape |
| Model latency makes a take 3 minutes of waiting | cut on the solve, not on the typing; caption any skipped wait |
| Daydream expires (3 min) mid-take | `/daydream` immediately before the blocked-tool beat, re-enter on retakes |
| Feed material missing for the account | daydream reads local memory files, not the network |
| Text illegible on a phone | captions carry the meaning; 18 px mono minimum; test at 390 px |
| X rejects the file | H.264 MP4, 30 fps, yuv420p, faststart, no audio |
| The concurrent art lane changes visuals mid-shoot | shoot after the freeze commit (`tasks.md` H25) |
