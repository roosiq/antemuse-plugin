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

## 3. Story beats and shot list (84 s)

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

## 5. Toolchain — what captures, what draws

| job | tool | state | why this one |
|---|---|---|---|
| record the screen | `Xvfb` + `xterm` + `ffmpeg -f x11grab` | **verified** 2026-11-08 | no window manager or GPU capture needed; 1280×720/30 fps, H.264 via `libopenh264`, 3 s ≈ 37 KB |
| drive the session | `tmux send-keys` via `tools/demo/human_type.py` | **built + tested** | deterministic retakes; pacing below |
| captions and cards | `tools/demo/overlays.py` (Pillow) → PNG per beat | **built + tested** | text lives in `beats.json`, not in an escaped ffmpeg string; brand palette enforced |
| composite | `ffmpeg overlay` with `enable='between(t,a,b)'` | **tested** | one filter graph, no editor, re-renders in seconds |
| optional desktop capture | OBS Studio (`dnf`, 5.1 MiB) | not installed | only worth it if the demo moves to the real desktop app; adds a GUI dependency |
| optional hand edit | Kdenlive / Shotcut | not installed | only if a human editor takes over the cut |
| generated stills | local SD at `:8089` | **not running** | the takeover already carries Meshy art; do not add a second art pipeline |

Not used, deliberately: OBS (headless Xvfb is enough), drawtext (quoting and
wrapping are the failure mode), screen-studio GUIs, AI avatars.

Palette and type come from `docs/brand.md`: ground `#0e0c0b`, amber `#f2b25a`,
teal `#4fa89c`, Liberation Mono. Captions are 34 px, one or two lines, on a warm
near-black band with an amber rule — the same grammar as the takeover, so the
overlay does not look bolted on.

## 5.1 The human, honestly

There is **no webcam on this machine**, and an AI avatar or synthetic voice would
read as generated — the opposite of the "real situation" the video needs. So the
human is conveyed by behaviour, not by a face:

- **Human pace.** `human_type.py` types at 45–145 ms per character, pauses longer
  at spaces and punctuation, and inserts one typo in the middle of a word that is
  noticed and backspaced. Seeded, so a retake matches the take.
- **A real task.** A scratch repository with a test that genuinely fails, and a
  real `hermes` session working on it. No mock terminal, no pre-baked output.
- **A real reason.** The session starts from the person's own words ("I've been
  on this for three hours"), not from a command list.
- **One visible hesitation.** The pause before `/break` and the typo are the two
  moments that make it read as a person.
- **Voice, only if real.** If a voice is wanted, Ryan records 20–30 s on a phone;
  no TTS. Otherwise the cut is music-free and caption-led, which is normal for
  muted X playback.

If a face is wanted later, the honest version is a 200 px webcam inset recorded
separately and composited with `ffmpeg overlay` — but there is no camera here, so
the plan does not depend on one.

## 5.2 Filter graph, exactly

```bash
python3 tools/demo/overlays.py render          # writes tools/demo/out/beat_NN.png
GRAPH=$(python3 tools/demo/overlays.py filter)
INPUTS=""; for f in tools/demo/out/beat_*.png; do INPUTS="$INPUTS -loop 1 -i $f"; done
ffmpeg -i take.mp4 $INPUTS -filter_complex "$GRAPH" -map "[v9]" \
  -c:v libopenh264 -b:v 6M -pix_fmt yuv420p -movflags +faststart demo.mp4
```

The chain overlays each card only inside its window, so one render covers all
nine beats; `beats.json` is the single source of timing and copy.

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

- Captions: generated as PNGs by `tools/demo/overlays.py` from `beats.json`
  (Liberation Mono 34 px, paper `#f7f3ee` on ground `#0e0c0b` at 91%, amber rule),
  composited by the ffmpeg chain in §5.2. Wrapping is measured in pixels, so no
  caption spills off a phone.
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
