# Contributing

Antemuse is a Hermes plugin: Python for the state engine and surfaces, a little
JavaScript for the desktop pane and the software scene rasteriser.

## Before you change behaviour

The record is the spec. Read `docs/spec.md` §18 ("must not change") first, then
the relevant change folder in `specs/changes/`. A behaviour change needs a spec
in that folder with acceptance criteria; a typo does not.

## Run the suite

```bash
tools/test.sh                    # ~30 s, temp data home, renderer tests skipped
tools/test.sh --with-renderers   # npm ci first, so the renderer tests run too
hermes plugins doctor antemuse
hermes plugins validate . --install-deps --json
```

`tools/test.sh` drops the exported `PYTHONPATH` (it breaks collection) and points
the plugin at a temporary data home, so a run never touches your real state.

## Style

- Plain sentences in user-facing strings. No exclamation marks, no jargon the
  person did not bring.
- No model call on entry, exit, expiry, or rendering. That is a product rule, not
  a performance preference.
- A state may change what the agent can do and what it says; it may not claim to
  make the agent more creative. `docs/spec.md` §16 has the evidence and its
  limits.
- Tests name the behaviour, not the implementation. If a test needs a private
  detail to pass, the behaviour is under-specified.

## Commits and pull requests

- One change per commit, with the reason in the message.
- Run the suite before opening a PR; paste the command and its result.
- Do not commit generated assets (`data/meshy/`, `docs/brand/gen/*.png`,
  `tools/demo/out/`) or caches.
- New to the surface? Say what the person sees and what the agent sees, and add
  the screenshot under `docs/screenshots/`.

## Licence

Contributions are accepted under the MIT licence in `LICENSE`.
