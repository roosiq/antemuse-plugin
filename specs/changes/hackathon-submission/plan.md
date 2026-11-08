# Hackathon submission — execution plan

Companion to [`spec.md`](spec.md). Times are EST. Deadline 2026-11-11 17:00.

Working assumption: **submit on Tue 2026-11-10 by 18:00**, one day of buffer.
The catalog PR may be pending at submission — HACK-01 accepts an opened PR.

---

## W0 — Unblock and freeze (Sun 11-08, ~30 min, human-gated)

| step | command | done when |
|---|---|---|
| re-auth GitHub | `gh auth login -h github.com` | `gh auth status` shows a valid token for `roosiq` |
| decide repo | public `roosiq/antemuse-plugin` | `gh repo view --json visibility` says `PUBLIC` |
| create + push | `git remote add origin git@github.com:roosiq/antemuse-plugin.git && git push -u origin main` | clone without credentials succeeds |
| freeze scope | this document | no new feature work enters the pin |

If Ryan prefers not to make the plugin public yet, the submission cannot happen:
rule PRE-01 has no exception and a private repo cannot be cloned by reviewers.

## W1 — Repo hygiene and pin (Sun evening → Mon morning, ~2 h)

1. Reconcile the working tree. Currently dirty: `tools/scene.html` (modified),
   `data/meshy/` (2.1 MB untracked), `data/meshy/history.json`.
   - `data/meshy/` is generated art output: keep it out of the pin, add
     `data/meshy/` to `.gitignore`.
   - `tools/scene.html` belongs to the in-flight art work. Commit it only if it is
     finished and the scene renders; otherwise `git stash` it for after the
     deadline. **The pin ships the last verified art, not work in progress.**
2. Add `LICENSE` (MIT). Compatible with bundled three.js (MIT) and the existing
   CC BY 4.0 attribution in `data/collider/`.
3. Extend `.gitignore` with `!docs/screenshots/*.png` so catalog screenshots can
   be committed past the blanket `*.png` rule.
4. Commit as one hygiene commit, then a **freeze commit** that is the pin.

Commands:

```bash
hermes plugins validate . --install-deps --json        # expect: all ok, warnings []
env -u PYTHONPATH NLTK_DATA=/home/ryan/nltk_data \
  ANTEMUSE_STATES_HOME=$(mktemp -d) \
  uvx --with pillow --with nltk --quiet pytest tests/ -q
# 677 collected, 7 skipped without npm ci — install and rerun so the pin has no skips
npm ci && env -u PYTHONPATH ... pytest tests/ -q
hermes plugins doctor .                                # expect: 1 tool, 8 hooks
git rev-parse HEAD                                     # the 40-char pin
```

Record the count and the date in `docs/spec.md` §13 and add a §15 change-log row
for `hackathon-submission` once the pin is cut.

## W2 — README, disclosures, screenshots (Mon, ~3 h)

1. Fix drift: `README.md:75` says "manifest: 1 tool, 4 hooks"; 8 hooks register.
2. Add a **Disclosures** section (rule 13), one line each:
   - reads public feeds during `doomscroll` (`core/social.py`);
   - optional image generation through `SD_SERVER`, default a tailnet host
     (`tools/gen_frames.py`), not required for normal use;
   - spawns a child process for the terminal takeover (`core/tui.py`);
   - dev-only scripts under `tools/` make network calls and are never imported by
     registration;
   - writes only under the plugin data dir; reads no credentials, no `.env`, no
     `auth.json`; no telemetry; no self-updater.
3. Add a first-screen summary: one paragraph, one screenshot, one command.
4. Capture 3–4 screenshots (PNG, committed under `docs/screenshots/`):
   takeover mid-walk, a chat postcard, `/break` recommendation, a blocked-tool
   refusal. These become the catalog `screenshots:` list (must be hosted under the
   pin) and the README gallery.

## W3 — Catalog entry and PR (Mon, ~1 h)

`plugin-catalog/antemuse.yaml` against a fresh clone of `NousResearch/hermes-agent`:

```yaml
name: antemuse
repo: https://github.com/roosiq/antemuse-plugin
sha: <40-char pin>
description: Deliberate, bounded changes to how the agent works — walk, daydream, dream, doomscroll — with tool policy, reply contracts, wordless imagery and an account on return.
maintainer: roosiq
tier: community
category: general
requires_hermes: ">=0.21.6"
version: "0.10.0"
docs_url: ""
readme: true
screenshots: [<raw.githubusercontent.com URLs at the pin>]
```

`version` is a human label; 0.10.0 avoids claiming the `1.0.0` that §19 reserves
for `scenes-per-surface`. PR description carries the rule-13 disclosures verbatim
and links the X demo once it exists (open the PR first, edit the description
after the video is posted).

## W4 — The demo (Mon capture, Tue edit; ~5 h total)

The single highest-leverage artifact. 90 seconds, mobile-legible, no narration
required, captions burned in.

**Shot list (target 82 s):**

| t | screen | what proves the claim |
|---|---|---|
| 0:00–0:06 | title card over a live session: "Antemuse — the agent changes state, not just prompt" | framing |
| 0:06–0:16 | `/break` → `break due · 96m since last state · 6 failed calls · walk recommended` | the plugin watches work and does arithmetic, no model call |
| 0:16–0:26 | `/dream` → new reply marker, `DREAMING · 30:00`, tools closed | a state is a contract, not a mood |
| 0:26–0:34 | agent attempts `terminal`; host refuses with the named message | **the host enforces it** — the beyond-a-prompt beat |
| 0:34–0:50 | `antemuse` takeover: full-screen imagery, clock, keys; hold on it | the visual surface, wordless by design |
| 0:50–1:02 | `/return` → the agent's account: where it went, what it touched, what happens next, then back to the task | the state ends with an account and the work resumes |
| 1:02–1:12 | `/states` in Discord: one postcard, no caption | one state, different surfaces, same dict |
| 1:12–1:20 | `hermes plugins validate` output, all green; `677 passed` | reliability evidence, on screen |
| 1:20–1:22 | end card: repo URL + catalog PR number | where to look |

Rules of the cut: no claim about creativity; no sped-up typing that hides a
failure; no fake terminal output — every line is a real run. If a take shows an
error, keep the error and caption what it was, or cut the take.

**Capture path (all installed):** `tmux` + a real terminal under `xvfb-run` +
`ffmpeg -f x11grab`, 1280×720, 30 fps, large mono font; then `ffmpeg` trim and
burn captions. `asciinema`/`agg` are not installed and are not needed.
Fallback: `ffmpeg` x11grab on the live display with a full-screen terminal.

## W5 — Publish and submit (Tue, ~45 min)

1. Post the video on X from Ryan's account, tag `@NousResearch`, link the repo.
2. Screenshot the post (URL + timestamp) into `submission/` outside the repo.
3. Submit the Typeform with the catalog PR URL and the X post URL.
4. Capture the confirmation; note the submission time in UTC and EST.

## W6 — Buffer (Wed 11-11, until 15:00)

Only two things may happen here: an X post that failed to upload is reposted, or a
catalog PR that a maintainer asked to change is amended. No code changes; a new
pin means rerunning W1's validation, which needs ~2 h.

---

## Copy drafts

**X post (short):** Antemuse gives a Hermes agent states it can actually enter —
walk, daydream, dream, doomscroll. The host enforces the tool policy; the person
sees pictures, never candidates. 90-second demo, catalog PR in the thread.
@NousResearch

**Repo one-liner:** A Hermes plugin that changes how the agent works for a bounded
time — which tools it may touch, what shape its reply takes, what it carries back.

**Catalog description (one line, schema limit):** Deliberate, bounded changes to
how the agent works, with host-enforced tool policy, reply contracts, wordless
imagery and an account on return.

---

## Risks and mitigations

| risk | likelihood | mitigation |
|---|---|---|
| GitHub auth stays broken; no public repo | medium | W0 first; ask Ryan immediately, everything else is independent |
| `.pyc`/generated art leaks into the pin | medium | fresh clone of the freeze commit + `git ls-files` grep for binaries before pinning |
| Screenshots rejected because `.gitignore` blocks PNG | high if forgotten | explicit `!docs/screenshots/*.png` and a `git check-ignore` proof |
| Catalog CI needs maintainer to start it | certain | submit the form with a pending PR; HACK-01 allows it |
| Video over 90 s or unreadable on a phone | medium | hard cap 82 s in the edit; check on a phone-sized player before posting |
| README disclosure omission found in review | medium | W2 checklist; PR repeats the same lines |
| The art work in flight destabilises the pin | medium | `data/meshy/` and unfinished `scene.html` stay out |
| Time lost to the immersive-visuals thread | high | it is explicitly out of scope until after 11-11 17:00 |

## Definition of done

`spec.md` §4 A1–A14 all evidenced, the form confirmation stored, and
`docs/spec.md` §15 carrying a `hackathon-submission` row with the pin, the PR
number, the X URL and the submission timestamp.
