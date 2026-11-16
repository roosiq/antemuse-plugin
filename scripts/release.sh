#!/usr/bin/env bash
# Cut a release only after the runtime, catalog media, and package gates agree.
#
# Usage: ./scripts/release.sh <version>
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:?usage: release.sh <version>}"
cd "$SRC"

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  ok    %s\n' "$*"; }
skip() { printf '  skip  %s\n' "$*"; }
die()  { printf '\n  FAILED: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "required command is unavailable: $1"; }

[[ -z "$(git status --porcelain)" ]] || die "working tree is dirty; commit or stash first"
for required in tar sed grep mktemp; do
  command -v "$required" >/dev/null 2>&1 || die "required command is unavailable: $required"
done

run_release_gates() {
  say "release gates"
  need python3
  need uvx

  local state_home
  state_home="$(mktemp -d)"
  trap 'rm -rf "$state_home"' RETURN
  env -u PYTHONPATH ANTEMUSE_STATES_HOME="$state_home" \
    uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q
  ok "test suite"

  if [[ -d tools/desktop_harness/node_modules || -d node_modules ]]; then
    need node
    node tools/desktop_harness/mount.mjs
    ok "desktop harness"
  else
    skip "desktop harness: no node_modules (run npm install in tools/desktop_harness)"
  fi

  if python3 -c 'import playwright.sync_api' >/dev/null 2>&1; then
    python3 tools/cockpit_harness.py
    ok "cockpit harness"
  else
    skip "cockpit harness: Python playwright is not installed"
  fi

  python3 tools/catalog_entry.py --check
  ok "catalog entry"
  python3 tools/make_screenshots.py --check
  ok "catalog screenshots"
}

verify_package() {
  local tarball="$1"
  local package="antemuse-$VERSION"
  local manifest_version init_version packed_version packed_init extract

  [[ -f "$tarball" ]] || die "build did not produce $tarball"
  manifest_version="$(sed -n 's/^version: "\(.*\)"/\1/p' plugin.yaml | head -1)"
  init_version="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' __init__.py | head -1)"
  packed_version="$(tar -xOf "$tarball" "$package/plugin.yaml" | sed -n 's/^version: "\(.*\)"/\1/p' | head -1)"
  packed_init="$(tar -xOf "$tarball" "$package/__init__.py" | sed -n 's/^__version__ = "\(.*\)"/\1/p' | head -1)"
  [[ "$manifest_version" == "$VERSION" && "$init_version" == "$VERSION" && \
     "$packed_version" == "$VERSION" && "$packed_init" == "$VERSION" ]] ||
    die "version mismatch: plugin.yaml version=$manifest_version, __version__=$init_version, tarball plugin.yaml version=$packed_version, tarball __version__=$packed_init, requested=$VERSION"
  ok "plugin.yaml version == __version__ == tarball plugin.yaml version == $VERSION"

  if tar -tzf "$tarball" | grep -E '(^|/)(\.git|\.antemuse)(/|$)|(^|/)__pycache__(/|$)|\.pyc$' >/dev/null; then
    die "tarball contains prohibited build residue (.pyc, __pycache__, .git, or .antemuse)"
  fi
  ok "tarball has no .pyc, __pycache__, .git, or .antemuse"

  extract="$(mktemp -d)"
  trap 'rm -rf "$extract"' RETURN
  tar -xzf "$tarball" -C "$extract"
  [[ -f "$extract/$package/BUILD-MANIFEST.json" ]] ||
    die "tarball did not extract BUILD-MANIFEST.json"
  python3 - "$extract/$package/BUILD-MANIFEST.json" "$VERSION" "$(git rev-parse HEAD)" <<'PY'
import json
import sys
from pathlib import Path

path, version, source_commit = map(Path, sys.argv[1:])
data = json.loads(path.read_text(encoding="utf-8"))
if data.get("version") != str(version):
    raise SystemExit(f"manifest version mismatch: {data.get('version')!r}")
if data.get("source_commit") != str(source_commit):
    raise SystemExit(f"manifest source commit mismatch: {data.get('source_commit')!r}")
assets = data.get("injected_assets")
if not isinstance(assets, list) or not assets:
    raise SystemExit("manifest has no injected projection assets")
for asset in assets:
    if not str(asset.get("path", "")).startswith("assets/projection/") or not asset.get("sha256"):
        raise SystemExit(f"invalid injected asset record: {asset!r}")
PY
  ok "BUILD-MANIFEST.json is present in the tarball and extracted tree"

  # The source tree passing means nothing if the package cannot collect its own tests: a test that
  # imports repository-only code (experiments/, specs/) errors at collection in the tarball, which
  # is exactly the tree a reviewer runs. Run the shipped suite from the extracted package.
  local packed_state
  packed_state="$(mktemp -d)"
  ( cd "$extract/$package" && env -u PYTHONPATH ANTEMUSE_STATES_HOME="$packed_state" \
      uvx --with-requirements requirements-test.txt --quiet pytest tests/ -q ) ||
    die "the extracted package cannot run its own test suite"
  rm -rf "$packed_state"
  ok "the extracted package runs its own suite"
}

run_release_gates

sed -i.bak -E "s/^version: \"[0-9.]+\"/version: \"$VERSION\"/" plugin.yaml
sed -i.bak -E "s/__version__ = \"[0-9.]+\"/__version__ = \"$VERSION\"/" __init__.py
rm -f plugin.yaml.bak __init__.py.bak
python3 tools/changelog.py
git add plugin.yaml __init__.py CHANGELOG.md
git commit -q -m "$VERSION: release"

# Build and verify the exact version-bump commit before adding its catalog entry. The catalog
# commit exists solely to pin this source commit; it must not become a hidden input to the tarball.
DIST="${ANTEMUSE_DIST:-$HOME/.cache/antemuse/dist}"
bash scripts/build-release.sh "$DIST"
verify_package "$DIST/antemuse-$VERSION.tar.gz"

# The catalog entry is separate because it pins the version-bump commit rather than pretending a
# commit can contain its own SHA.
python3 tools/catalog_entry.py --pin "$(git rev-parse HEAD)"
git add plugin-catalog/antemuse.yaml
git commit -q -m "catalog entry for $(git rev-parse --short=12 HEAD~1)"
printf '\nrelease %s\n  pinned: %s\n  entry : %s\n' "$VERSION" \
  "$(sed -n 's/^sha: //p' plugin-catalog/antemuse.yaml)" "$(git rev-parse --short=12 HEAD)"
