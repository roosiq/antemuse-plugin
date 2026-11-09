# Generated assets live off-repo

The paid and generated artwork is not in this tree. On 2026-11-09 it was moved to
`/home/ryan/antemuse-assets/2026-11-09/` (101 files, 61.8 MB) with a manifest and
restore instructions:

```
data/meshy/pack/            the Meshy asset pack and its append-only ledger
data/meshy/*/card*.png      rasterised state cards
docs/brand/gen/*.png        generated brand experiments
docs/brand/marks/*.png      generated marks and icons
```

Tracked files stayed: the Meshy manifests and three GLBs under `data/meshy/`, the
brand HTML/TXT sources under `docs/brand/gen/`, and every document.

Nothing in the suite, the live renderer, or `plugin.yaml` reads the moved files —
`tools/test.sh` is unchanged at 906 passed, 1 skipped without them. `tools/gen_pack.py`
and the brand tooling write to the old paths, so re-running them recreates the
directories rather than failing.

They cost real Meshy credits; restore rather than regenerate:

```bash
cd /home/ryan/antemuse-assets/2026-11-09 &&
  find . -type f -not -name 'MANIFEST*' -print0 |
  rsync -a --from0 --files-from=- . /home/ryan/antemuse-plugin/
```
