# Packaging audit — 2026-11-09

What an admitted plugin looks like, measured rather than guessed: every entry in
the shipped catalog (`~/.hermes/hermes-agent/plugin-catalog`, **763 entries**) and
the eight approved plugins installed on this machine, compared with this tree.

## What the catalog actually requires

Field frequency across the 763 entries:

```
name, repo, sha, description, maintainer, tier, category, capabilities   99%
docs_url                                                                 93%
version                                                                  82%
platforms                                                                66%
requires_hermes                                                          63%
subdir                                                                   31%
image                                                                    30%
title                                                                    22%
readme                                                                   19%
screenshots                                                              14%
known_issues                                                              9%
onboarding, homepage_url, requires_env                                     <1%
```

Tiers: 741 community, 17 official, 4 verified. Categories: tools 247, desktop 174,
memory 67, models 66, general 53, automation 49, web 42, platform 41, voice 21.

The loader (`hermes_cli/plugin_catalog.py`) validates a flat mapping and rejects
an entry with no full 40-char `sha`, an invalid category, or a non-`https://` repo.
`version` must be a **quoted string** — an unquoted `0.9.0` fails admission.

## What approved plugins ship

Root files in the eight installed plugins:

| file | count | this repo |
|---|---|---|
| `LICENSE` | 8/8 | yes |
| `README.md` | 8/8 | yes |
| `plugin.yaml` | 8/8 | yes |
| `tests/` | 8/8 | yes |
| `CHANGELOG.md` | 4/8 | **was missing — added** |
| `SECURITY.md` | 3/8 | **was missing — added** |
| `CONTRIBUTING.md` | 2/8 | **was missing — added** |
| `pyproject.toml` | 5/8 | no — not a pip package; `pytest.ini` added instead |
| `docs/` | 5/8 | yes |
| `dashboard/` | 4/8 | yes |

Manifest fields across those eight (`plugin.yaml`), versus this one:
`license`, `tags`, `manifest_version`, `platforms` were absent here and are the
only fields the manifest schema knows that we lacked. `provides_commands` (2/8)
and `optional_env` (1/8) are optional and not applicable — commands are declared
by registration, and no env vars are required.

## Defects found and fixed in this pass

1. **Two catalog schemas, one of them invalid.** `plugin-catalog/antemuse.yaml`
   was generated in a homegrown shape (`label`, `author`, `homepage`,
   `source: {type, repo, ref}`) that the loader silently drops — it has no `repo`
   or `sha` field at top level. The staged entry in `specs/` used the real schema.
   `tools/catalog_entry.py` now emits the loader's schema, and the generated file
   pins `9d4ec4c` (the validated commit) with `--pin`.
2. **Unquoted version.** The generator wrote `version: 0.9.0`; the judge fails that
   ("version must be a quoted string"). The generator now quotes it.
3. **Manifest surface.** Added `manifest_version: 2`, `license: MIT`,
   `tags: [state, cognition, workflow, terminal, creativity]`,
   `platforms: [linux, macos]`.
4. **Repo documents a reviewer looks for.** Added `CHANGELOG.md`, `SECURITY.md`
   (network, reads, writes, child process, untrusted text, reporting), and
   `CONTRIBUTING.md` (spec rule, test command, style, commit rules).
5. **README sections.** Added `Compatibility`, `Known limitations`, and `Licence`.
   Approved plugins carry equivalents (`Security model`, `Known limitations`,
   `Compatibility`, `How to test`).
6. **Catalog optional fields.** Added `title` and three `known_issues` (desktop
   pane unverified, profile-wide state, gated exploration library). `screenshots`
   ships empty and `image` is omitted — both need a public raw.githubusercontent
   URL, so they can only be filled after the repo is public.
7. **Test-run hygiene.** `pytest.ini` with `testpaths`; the `-q` in
   `tools/test.sh` was doubled by a `addopts = -q`, which silently hid the pass
   count. Removed.

## Still missing, and why

| gap | blocked by |
|---|---|
| Public repo at the pin (PRE-01) | `gh auth login`; no remote exists |
| Catalog PR (PRE-04) | depends on the public repo |
| `image:` + `screenshots:` | need raw.githubusercontent URLs at the pin |
| Demo URL, duration, tag | not recorded yet |
| Form submission | depends on the two links |

Nothing else in the packaging comparison is outstanding. `hermes plugins validate`
is 16/16 with no warnings, and the judge's local fail checks are clear; the
remaining rows are the four external artifacts plus manual quality review.
