#!/usr/bin/env bash
# Build the installable Antemuse package with a provenance manifest: a fresh Hermes install can
# take the tarball as-is, and a reviewer can identify every projection byte injected from cache.
#
# Only what runs ships. The evaluation corpus and experiment outputs stay in the repository —
# they are evidence, not runtime, they are 13 MB of someone else's prose, and the install-time
# security scanner correctly treats arbitrary model output in a plugin as untrusted text.
#
# The tests travel with the package on purpose: a claim about behaviour is only checkable by
# whoever has the artifact, and an independent verifier should be able to run the same tests on
# the same bytes rather than take a report's word for it.
#
#   usage:  ./scripts/build-release.sh [--out DIR]
#
# The build validates the packed tree with the same gate a catalog reviewer runs, so a package
# that cannot be installed is never produced.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Outside the checkout by default: the package carries 117k WordNet labels, and building inside
# the tree puts them back under the retired-name scan.
OUT="${1:-${ANTEMUSE_DIST:-$HOME/.cache/antemuse/dist}}"
VERSION="$(sed -n 's/^version: "\(.*\)"/\1/p' "$SRC/plugin.yaml" | head -1)"
[[ -n "$VERSION" ]] || { echo "FAILED: cannot read version from $SRC/plugin.yaml" >&2; exit 1; }
NAME="antemuse-$VERSION"
STAGE="$OUT/$NAME"

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  ok    %s\n' "$*"; }
die()  { printf '\n  FAILED: %s\n' "$*" >&2; exit 1; }

say "build $NAME"
mkdir -p "$OUT"
rm -rf "$STAGE" "$OUT/$NAME.tar.gz"

# Runtime only.
if command -v rsync >/dev/null 2>&1; then
  rsync -a \
    --exclude .git --exclude node_modules --exclude __pycache__ --exclude .pytest_cache \
    --exclude .venv --exclude experiments --exclude evaluation --exclude specs --exclude site \
    --exclude plugin-catalog --exclude dist --exclude .post-staging --exclude .antemuse \
    --exclude data/meshy --exclude .work \
    "$SRC"/ "$STAGE"/
else
  cp -a "$SRC" "$STAGE"
  rm -rf "$STAGE"/{.git,node_modules,experiments,evaluation,specs,site,plugin-catalog,dist,.antemuse,.work}
  rm -rf "$STAGE/data/meshy"
  find "$STAGE" -name __pycache__ -prune -exec rm -rf {} +
fi
# The pane is the only thing the desktop loads. The baked scenes were deleted from the renderer
# but their files are still in the checkout; shipping them lets an older pane find them, and a
# backup of a truncated file has no business on anyone's install.
rm -rf "$STAGE/desktop/art" "$STAGE/desktop/vendor" "$STAGE/desktop/scene3d.js"
find "$STAGE/desktop" -name '*.bak' -delete 2>/dev/null || true
ok "staged $(du -sh "$STAGE" | cut -f1)"

# Every local link a shipped document makes must resolve inside the package. The README
# pointed at docs/EXAMPLES.md for three releases while the packer dropped docs/ entirely, and
# the test that checked the README only ever looked for the string, never for the file.
say "links in the shipped documents"
python3 - "$STAGE" <<'PY'
import re, sys
from pathlib import Path

stage = Path(sys.argv[1])
broken = []
for doc in ("README.md", "TESTING.md", "CONTRIBUTING.md", "SKILL.md", "SECURITY.md"):
    path = stage / doc
    if not path.exists():
        continue
    for target in re.findall(r"\]\((?!https?:|#|mailto:)([^)]+)\)", path.read_text(encoding="utf-8")):
        target = target.split("#", 1)[0].strip()
        if not target:
            continue
        if not (stage / target).exists():
            broken.append(f"{doc} -> {target}")
if broken:
    print("\n  FAILED: shipped documents link files the package does not carry:")
    for one in broken:
        print(f"    {one}")
    sys.exit(1)
print("  ok    every local link resolves inside the package")
PY

# The projection travels WITH the package but not in the repository: it carries 117k WordNet
# labels, and the retired-name rule forbids those words anywhere in the tree. It is built by
# tools/project_wordnet.py and cached under the user's cache dir.
PROJ_SRC="${XDG_CACHE_HOME:-$HOME/.cache}/antemuse"
mkdir -p "$STAGE/assets/projection"
if [[ -f "$PROJ_SRC/wordnet.proj.json" && -f "$PROJ_SRC/wordnet.proj.f16" ]]; then
  cp -f "$PROJ_SRC/wordnet.proj.json" "$PROJ_SRC/wordnet.proj.f16" "$STAGE/assets/projection/"
  ok "projection bundled from $PROJ_SRC"
else
  die "no wordnet projection at $PROJ_SRC — run tools/project_wordnet.py, then build again"
fi

# The projection is intentionally injected from the local cache rather than committed: preserve
# its exact source and digest in the artifact, or a tarball cannot be reproduced or reviewed.
SOURCE_COMMIT="$(git -C "$SRC" rev-parse HEAD)"
BUILT_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python3 - "$STAGE/BUILD-MANIFEST.json" "$SOURCE_COMMIT" "$VERSION" "$BUILT_AT" "$STAGE/assets/projection" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

manifest, source_commit, version, built_at, projection = map(Path, sys.argv[1:])
# Keep textual values as strings after Path's platform-safe argument transport.
source_commit, version, built_at = map(str, (source_commit, version, built_at))
projection = Path(projection)
assets = []
for path in sorted(p for p in projection.rglob("*") if p.is_file()):
    assets.append({
        "path": path.relative_to(projection.parent.parent).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size": path.stat().st_size,
    })
Path(manifest).write_text(json.dumps({
    "source_commit": source_commit,
    "version": version,
    "built_at": built_at,
    "injected_assets": assets,
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
ok "wrote BUILD-MANIFEST.json for ${#SOURCE_COMMIT}char source commit and ${VERSION}"

say "validate the packed tree (the catalog gate)"
hermes plugins validate "$STAGE" >/tmp/antemuse-validate.log 2>&1 || {
  tail -15 /tmp/antemuse-validate.log
  die "the packed tree failed validation — see above"
}
ok "validation passed"

# Validation imports the package, and importing writes bytecode into the staged tree — 104 .pyc
# reached 0.10.15 this way, plus the walk cursor the plugin kept in the working directory. The
# exclusions above cannot help: these files did not exist when rsync ran. Prune after the gate,
# then assert, so "the artifact is what the script built" is checkable rather than assumed.
find "$STAGE" -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -name '*.pyc' -delete 2>/dev/null || true
rm -rf "$STAGE/.pytest_cache" "$STAGE/.antemuse"
left="$(find "$STAGE" \( -name '*.pyc' -o -name '__pycache__' -o -name '.antemuse' \) | head -5)"
[[ -z "$left" ]] || die "the staged tree still carries build residue: $left"
ok "no bytecode or local state in the package"


say "pack"
tar -C "$OUT" -czf "$OUT/$NAME.tar.gz" "$NAME"
ok "$OUT/$NAME.tar.gz ($(du -h "$OUT/$NAME.tar.gz" | cut -f1))"
printf '  sha256  %s\n' "$(sha256sum "$OUT/$NAME.tar.gz" | cut -d' ' -f1)"
