# Demo — 90 seconds, shot by shot

For A7 of `hackathon-submission`. The video shows the **mechanism** and the **experience**.
It never claims a benefit: no "this made the work better", no score, no before/after
quality comparison. The wording is fixed here so it cannot drift during editing.

Total budget **84 s**, leaving 6 s of headroom under the 90 s limit — an over-run is a
disqualifying detail, not a rounding error.

| # | time | on screen | what proves it |
|---|---|---|---|
| 1 | 0–6 s | Terminal. `/walk` typed, then `/return`. | Six commands exist; a state is one line away and one line to leave. |
| 2 | 6–20 s | `antemuse` takeover: full-screen wordless scene, live keys. | The picture is real, generated, and takes the pane. Text is cut to a title. |
| 3 | 20–34 s | Split: the injected block on the model side (directive + material) and the card the person receives. | The audiences are separated by construction: no candidate text reaches the human surface. |
| 4 | 34–46 s | `state(action="status")` while the state runs, then the state ending **by itself** at its dose. | The clock is not what ends it; the dose is. This is the claim, and it is visible. |
| 5 | 46–58 s | An expiry: a state stopped at its ceiling prints `expired before its dose: 2 of 3`. | A named failure, not a blank screen (A14). |
| 6 | 58–68 s | `hermes plugins doctor antemuse` → 1 tool, 8 hooks; `hermes plugins validate` → 16/16 ok, no warnings. | Reliability and polish, shown from the tooling a reviewer would run. |
| 7 | 68–78 s | Settings ▸ Plugins ▸ Antemuse: six settings, one toggled. | It is a Hermes surface, not a standalone app. |
| 8 | 78–84 s | Title card: name, repo, one sentence — "The agent takes the state; the host enforces it." Tag `@NousResearch`. | Rule compliance: the tag and a public repo URL. |

## Recording notes

- Terminal: truecolor, 120×34, no font smoothing; the takeover wants vertical room.
- One take per shot, then cut. No sped-up footage of a state's own turn — the speed is
  part of the claim.
- The audio is a caption track, no voice: the only spoken claim is the last card.
- Words that must not appear anywhere in the video or its caption: "creative", "better",
  "improves", "quality score", "benchmark".

## Shot 4 in detail (the load-bearing one)

```
/state → status shows: turns served 4 of 6 · 0m of 3m ceiling
… the agent works, the dose completes …
DREAMING finished · the act is done, so the state is over.
```

The state ends without anyone typing anything, and without the clock reaching 3 minutes.
If the take does not show that, the take is wrong, not the claim.

## Failures to stage honestly (A14)

At least two of these must appear on screen, with the real string the code prints:

- a feed that cannot be read (`hn unreachable · …`)
- `nltk` corpus missing for a walk
- a tool refused by the state (only when the entry passed `block: true`)
- an expiry before the dose
