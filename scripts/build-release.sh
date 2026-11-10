#!/usr/bin/env bash
# Build the installable Antemuse package: a tarball a fresh Hermes install can take as-is.
#
# Only what runs ships. The evaluation corpus and experiment outputs stay in the repository —
# they are evidence, not runtime, they are 13 MB of someone else's prose, and the install-time
# security scanner correctly treats arbitrary model output in a plugin as untrusted text.
#
#   usage:  ./scripts/build-release.sh [--out DIR]
#
# The build validates the packed tree with the same gate a catalog reviewer runs, so a package
# that cannot be installed is never produced.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$SRC/dist}"
VERSION="$("$SRC/scripts/version.sh" 2>/dev/null || sed -n 's/^version: "\(.*\)"/\1/p' "$SRC/plugin.yaml" | head -1)"
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
    --exclude docs --exclude tests --exclude plugin-catalog --exclude dist \
    "$SRC"/ "$STAGE"/
else
  cp -a "$SRC" "$STAGE"
  rm -rf "$STAGE"/{.git,node_modules,experiments,evaluation,specs,site,docs,tests,plugin-catalog,dist}
  find "$STAGE" -name __pycache__ -prune -exec rm -rf {} +
fi
ok "staged $(du -sh "$STAGE" | cut -f1)"

# The projection: without it concepts fall back to a plain circle instead of the semantic layout.
[[ -f "$STAGE/assets/projection/wordnet.proj.json" ]] \
  || die "assets/projection/wordnet.proj.json missing — run tools/project_wordnet.py and re-copy it into assets/projection/"

say "validate the packed tree (the catalog gate)"
hermes plugins validate "$STAGE" >/tmp/antemuse-validate.log 2>&1 || {
  tail -15 /tmp/antemuse-validate.log
  die "the packed tree failed validation — see above"
}
ok "validation passed"

say "pack"
tar -C "$OUT" -czf "$OUT/$NAME.tar.gz" "$NAME"
ok "$OUT/$NAME.tar.gz ($(du -h "$OUT/$NAME.tar.gz" | cut -f1))"
printf '  sha256  %s\n' "$(sha256sum "$OUT/$NAME.tar.gz" | cut -d' ' -f1)"
