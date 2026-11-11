# Contributing

Antemuse is a Hermes plugin: Python for the state engine, one plain JavaScript file for the
desktop pane. The repository root **is** the plugin root — `plugin.yaml`, `__init__.py` and
`core/` sit at the top level, and Hermes loads it through the symlink
`~/.hermes/plugins/antemuse` → this directory.

## Rules that are not negotiable

- **No model call on entry, exit, expiry, or rendering.** That is a product rule, not a
  performance preference: a state has to work when the model is slow or absent.
- **A state may change what the agent can do and what it says. It may not claim to make the
  agent more creative.** The evidence for what a state does, and its limits, is in
  `experiments/idea-states/BENCHMARK.md`.
- **The six commands are the public contract.** `/walk /daydream /doomscroll /dream
  /unstuck /return`. Adding a verb means changing that contract deliberately; a plural
  neighbour (`/states` beside `/state`) is a past defect, and the suite fails on it.
- **One token, one meaning.** `/state` was a command that rendered a picture, and `/states`
  was the same picture under a plural. Both are gone: `state(action="status")` is the record,
  and the picture is the pane.
- Plain sentences in user-facing strings. No exclamation marks, no jargon the person did not
  bring.
- Tests name the behaviour, not the implementation. If a test needs a private detail to
  pass, the behaviour is under-specified.

## Run the suite

```bash
tools/test.sh                    # temp data home, pane renderer tests skipped
tools/test.sh --with-renderers   # npm ci first, so the renderer tests run too
hermes plugins doctor antemuse
hermes plugins validate . --install-deps   # what catalog CI runs
```

`tools/test.sh` drops the exported `PYTHONPATH` (it breaks collection) and points the plugin
at a temporary data home, so a run never touches your real state.

## Change something

1. Change the behaviour and the test that names it in the same commit.
2. Run the suite. Paste the command and its result in the pull request; a green claim without
   a command is not evidence.
3. If the change touches what a person sees, say what the person sees and what the agent
   sees, and refresh the screenshot under `docs/screenshots/` if the pane changed.
4. `./scripts/release.sh <version>` bumps the manifest, rewrites the changelog from commit
   subjects, regenerates `plugin-catalog/antemuse.yaml` and packs a validated tarball. Do not
   hand-edit the version fields or the catalog entry.

## Commits and pull requests

- One change per commit, with the reason in the message.
- Do not commit generated assets or caches (`node_modules/`, `__pycache__/`, `dist/`).
- The catalog entry pins a commit SHA: a version bump is a release, not a push.

## Licence

Contributions are accepted under the MIT licence in `LICENSE`.
