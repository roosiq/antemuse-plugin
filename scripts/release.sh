#!/usr/bin/env bash
# Cut a release in one pass: bump, regenerate the two generated documents, commit, pack, verify.
#
# The order is the part that keeps going wrong. The catalog entry pins a commit, so it has to be
# generated AFTER the code lands; the changelog is derived from commit subjects, so it has to be
# written BEFORE, and it must not announce the entry commit it cannot know. Anything that needs a
# number this process will produce later is excluded from the changelog rather than guessed
# (tools/changelog.py skips "catalog entry for ..." subjects for exactly that reason).
#
#   ./scripts/release.sh 0.10.20
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:?usage: release.sh <version>}"
cd "$SRC"

[[ -z "$(git status --porcelain)" ]] || { echo "working tree is dirty; commit or stash first" >&2; exit 1; }

sed -i.bak -E "s/^version: \"[0-9.]+\"/version: \"$VERSION\"/" plugin.yaml
sed -i.bak -E "s/__version__ = \"[0-9.]+\"/__version__ = \"$VERSION\"/" __init__.py
rm -f plugin.yaml.bak __init__.py.bak
python3 tools/changelog.py
python3 tools/spec_audit.py >/dev/null
git add -A && git commit -q -m "$VERSION: release"
python3 tools/catalog_entry.py
git add -A && git commit -q -m "catalog entry for $(git rev-parse --short=12 HEAD~1)"
bash scripts/build-release.sh
printf '\nrelease %s\n  pinned: %s\n  entry : %s\n' "$VERSION" \
  "$(sed -n 's/^sha: //p' plugin-catalog/antemuse.yaml)" "$(git rev-parse --short=12 HEAD)"
