# Demo — production plan (v2)

Status: **planned 2026-11-10, nothing recorded.** Supersedes v1 (2026-11-08). v1 was
built around the chat card and a terminal-only take. Since 0.9.36 chat carries no
visualization and the desktop pane is the picture, so the take moves into Hermes
Desktop with one short terminal beat. v1's verified terminal rig and its two
isolation traps are kept below. Task ids H40–H45 in [`tasks.md`](tasks.md).

Artifact: one public X post, video **strictly under 90 s**, showing the plugin
running, tagging `@NousResearch`. Target **82 s**, 1280×720, H.264, yuv420p,
faststart. Form closes **2026-11-11 17:00 EST**.

## 1. The claim, in one sentence

> A walk is a state the agent takes while it works: distant concepts arrive in
> *this* conversation, you watch them light up on the map, and when it ends the
> agent comes back with where it went.

Not claimed anywhere (picture, caption, post): that the agent becomes more
creative, better or faster, or that outputs improve. `docs/spec.md` §16 has no
evidence for it and §18 forbids the claim. Banned words in captions and post:
*creative, better, improves, smarter, boost, benchmark, score*.

## 2. Viewing conditions

Watched on a phone, muted, about 390 px wide:

- burned-in captions, one idea per shot; no voiceover; sound never carries meaning;
- the pane is the hero: large, centred, given time to breathe;
- chat text is evidence, not the message. The caption states the point.

## 3. Shot list (82 s)

Surface: **Hermes Desktop**, chat left, Antemuse pane right, one window. Shot 6
is the only terminal beat. Strings in column 4 were produced by the real plugin
at 0.10.0 on 2026-11-10; the take must show the plugin's own words.

| # | t | on screen | real string it must show | caption |
|---|---|---|---|---|
| 1 | 0:00–0:06 | Desktop, a real task mid-conversation (§4). The pane shows the whole concept space, dim. | pane chip `no state` | **Your agent, mid-task.** |
| 2 | 0:06–0:14 | Type `/walk`. Reply line appears; the chip flips. | `WALKING · 3 min · 6 turn(s) · work continues · distant concepts, still a path back to the task` | **/walk — it keeps working.** |
| 3 | 0:14–0:32 | Hold on the pane, no cuts. Hops land as warm points, the trail draws, edges to lit nodes go warm. Two or three hops. | lit labels (WordNet terms) | **Each hop lands far from the task — still on a path back to it.** |
| 4 | 0:32–0:46 | The next real question. The reply works the task, using a hop only where it bears on it. Marker ends the reply. | `— walking, 2 min left · /return to come back` | **What it passes goes into this conversation, and no other.** |
| 5 | 0:46–0:56 | `/return`. The account appears; the pane goes back to the whole space. | `WALKING ended · walk 1m · N step(s) · <from>→<to> [far]` then `The frame you were in is gone. State the goal, name the approach you were stuck in, then take a different first step.` | **It comes back with where it went.** |
| 6 | 0:56–1:06 | Terminal: `/state picture` → full-screen takeover, live scene, about 6 s, exit. | takeover frame, no words | **In a terminal, the whole screen.** |
| 7 | 1:06–1:14 | Settings ▸ Plugins ▸ Antemuse: five settings; hover *Follow suggestions automatically* (off). | the five labels | **It suggests. It starts nothing unless you say so.** |
| 8 | 1:14–1:22 | End card on black: wordmark, repo URL, catalog PR number. | `github.com/roosiq/antemuse-plugin` · `hermes-agent#NNNN` | **antemuse — a Hermes plugin** |

8 s of headroom. A take that runs past 86 s is re-cut, never sped up. A cut that
hides a wait is captioned `(20 s later)`; nothing is speed-ramped across a hop.

**Dropped from v1, and why.** The *blocked tool call* is real but opt-in
(`block: true`); it explains a setting rather than showing a state, and it stays
in the catalog screenshots. *Validator and test counts* belong to the reviewer and
go in the PR body; on a phone they are noise. The *chat card* no longer exists.

## 4. The task in the frame

The walk needs a real task to walk from, or the hops have no anchor and shot 4
is fake. Use one a viewer follows in two seconds:

> "Name this function — it merges two sorted lists and drops duplicates."

with a six-line Python function pasted in. **Do not script the agent's reply.**
Take the reply it gives. If no hop bears on the work, the reply ignores them
honestly and the caption still holds. Re-take rather than edit.

## 5. Preconditions

Each of these is a reason a take has failed before.

- **Version on camera = the pin.** The pane polls `/api/plugins/antemuse/state`.
  Before rolling, check `plugin:` in the payload equals the manifest version. A
  gateway still holding old modules is the commonest wrong-picture cause; restart
  it from a shell outside the gateway.
- **The ground has structure.** Use the real profile, or run
  `python scripts/install.py` (first-ledger scan) in the demo home. Idle, the pane
  should show ≥ 1,000 points.
- **Hops land on camera.** Walk hops are paced by turns, not a timer. Before shot
  3, confirm with `state(action="status")` that a hop lands per turn, and send the
  shot-4 question only after two or three have lit. If none lights in 20 s, stop:
  the take is wrong, not the claim.
- **No accidental rut line.** Fixed in 0.10.0: `recommend._rut` compared the
  running state with itself, so every walk said *this looks like a rut*. The real
  rut line still fires if the profile's previous state was a walk, so enter and
  `/return` a different state first.
- **Nothing private in frame.** Fresh session title, session sidebar hidden, no
  memory text, no paths with a username, no other plugins' chips.
- **Takeover beat.** Truecolor terminal, about 160×45, font ≥ 18 px, `node` on
  PATH. Without `node` it shows cached frames; check it animates before rolling.

### Isolation (kept from v1)

- **Trap 1: the live gateway runs the code it loaded.** Never infer demo behaviour
  from the agent you are talking to. Rehearse in a fresh process on the pin.
- **Trap 2: a state in the live profile reaches real work.** Since 0.9.36 a state
  reaches only the conversation that entered it, so this is contained, but
  rehearse in a throwaway `HERMES_HOME` anyway. `/return` from that conversation,
  or `state(action="exit")`, is the way out.

## 6. Capture and edit

| job | tool | state |
|---|---|---|
| desktop capture | **open decision.** The host session is Wayland, so `x11grab` cannot see the app, and no recorder is installed. Options: OBS Studio with PipeWire capture (`dnf install obs-studio`), or `gpu-screen-recorder`. GNOME's built-in recorder caps at 30 s, too short for one take. | decide before 11-11 morning |
| terminal capture (shot 6) | `Xvfb` + `xterm` + `ffmpeg -f x11grab`, via `tools/demo/capture.sh start\|record\|stop` | **verified** 2026-11-08 |
| keystrokes | `screenkey -M` in the terminal; typed by hand in Desktop | verified for the terminal |
| captions and cards | `tools/demo/overlays.py render` → one PNG per beat, from `tools/demo/beats.json` | built + tested; `beats.json` updated to §3 |
| composite | `ffmpeg` overlay chain from `overlays.py filter`, `enable='between(t,a,b)'` per card | tested |
| encode | `-c:v libopenh264 -b:v 6M -pix_fmt yuv420p -movflags +faststart -vf scale=1280:720` | tested |
| measure | `ffprobe -v error -show_entries format=duration -of csv=p=0 demo.mp4` | — |

```bash
python3 tools/demo/overlays.py render          # tools/demo/out/beat_NN.png
GRAPH=$(python3 tools/demo/overlays.py filter)
INPUTS=""; for f in tools/demo/out/beat_*.png; do INPUTS="$INPUTS -loop 1 -i $f"; done
ffmpeg -i take.mp4 $INPUTS -filter_complex "$GRAPH" -map "[v8]" \
  -c:v libopenh264 -b:v 6M -pix_fmt yuv420p -movflags +faststart -vf scale=1280:720 demo.mp4
```

Palette and type from `docs/brand.md`: ground `#0e0c0b`, amber `#f2b25a`, teal
`#4fa89c`, Liberation Mono. Captions 34 px, one or two lines, warm near-black band
with an amber rule. Hard cuts only. No transitions, zooms or fake glow.

## 7. The post

> antemuse — a Hermes plugin that lets your agent take a walk while it works.
> Distant concepts land in the conversation, you watch them light up on the map,
> and it comes back with where it went.
>
> github.com/roosiq/antemuse-plugin @NousResearch

No performance claim.

## 8. Acceptance (fill in after recording)

| # | check | target | measured |
|---|---|---|---|
| D1 | duration (`ffprobe`) | 78–86 s, strictly < 90.0 | — |
| D2 | every on-screen string reproducible by repeating the commands; no edited output | yes | — |
| D3 | captions legible at 390 px wide | yes | — |
| D4 | plugin version in payload during the take | = pin | — |
| D5 | hops lit on camera in shot 3 | ≥ 2 | — |
| D6 | banned words in captions and post | 0 | — |
| D7 | private text in frame | none | — |
| D8 | post public, plays logged out, tags `@NousResearch`; repo URL resolves | yes | — |
| D9 | Ryan signs off on a phone-size watch before posting | yes | — |

## 9. Fallbacks

- **Pane does not paint in the app:** record the full-window `/antemuse` route
  instead of the dock (same renderer, more room). If that fails too, use the
  in-page capture that made `docs/screenshots/pane-walk.png`, and say in the post
  that it is a pane render. Never present a render as a screen recording.
- **Shot-4 reply is weak or off-task:** re-take. After two failures, cut shot 4
  to 6 s on the marker line alone and give the time to shot 3.
- **Takeover misbehaves:** drop shot 6 and extend shot 3 by 6 s. The video stands
  without it.
- **Model latency:** cut on the solve, not the typing; caption the skipped wait.
