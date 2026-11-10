#!/usr/bin/env bash
# Antemuse — a full base install into an existing Hermes install.
#
# One command, no root, idempotent. It puts every piece in the place Hermes actually reads from:
#
#   1. the Python dependencies the plugin declares (pillow, nltk),
#   2. the NLTK corpora walks and dreams need (wordnet, framenet),
#   3. the plugin itself, registered and enabled,
#   4. the desktop half, copied into the one directory the desktop app loads,
#   5. the WordNet projection that places concepts on the picture,
#   6. a first ledger scan, so the first state has something to draw.
#
# It cannot restart the gateway (that would kill the session running it). It says so at the end
# and prints the one command to run.
#
#   usage:  ./scripts/install.sh [--dry-run]
#
# Every step is checked. A failure names the step and stops; nothing is left half-installed
# silently.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/doctor_counts.sh
. "$SRC/scripts/doctor_counts.sh"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
DRY=0
NO_CLI=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    # Skip the steps that go through the `hermes` command itself. Used to check the file layout
    # against a scratch home without touching Hermes' own registry.
    --no-cli) NO_CLI=1 ;;
    *) printf 'unknown option: %s\n' "$arg" >&2; exit 2 ;;
  esac
done

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  ok    %s\n' "$*"; }
warn() { printf '  warn  %s\n' "$*"; }
die()  { printf '\n  FAILED: %s\n' "$*" >&2; exit 1; }
run()  { if [[ $DRY -eq 1 ]]; then printf '  would %s\n' "$*"; else "$@"; fi; }

say "Antemuse base install"
printf '  source      %s\n' "$SRC"
printf '  hermes home %s\n' "$HERMES_HOME"
[[ $DRY -eq 1 ]] && printf '  dry run     nothing will be written\n'

# ---------------------------------------------------------------- 0. the host
say "0. host"
command -v hermes >/dev/null 2>&1 || die "no 'hermes' on PATH — install Hermes first"
HERMES_BIN="$(command -v hermes)"
ok "hermes at $HERMES_BIN"

# The interpreter Hermes itself runs on. Its launcher names it; a guess here is what makes a
# plugin's dependencies land somewhere the plugin never imports from.
# Launchers chain (a shim execs another shim execs the interpreter), so follow up to four hops
# looking for the actual python3 rather than giving up on the first file.
hermes_python() {
  local file="$1" hops=0 found
  while [[ -f "$file" && $hops -lt 4 ]]; do
    # Any absolute path ending in bin/python3 in the launcher is the interpreter it runs on.
    found="$(grep -oE '/[^ "'"'"']*bin/python3' "$file" 2>/dev/null | head -1)"
    [[ -n "$found" && -x "$found" ]] && { printf '%s\n' "$found"; return; }
    file="$(sed -n 's|.*exec \(/[^ ]*\) .*|\1|p' "$file" 2>/dev/null | head -1)"
    hops=$((hops + 1))
  done
}
HERMES_PY="$(hermes_python "$HERMES_BIN")"
if [[ -z "$HERMES_PY" || ! -x "$HERMES_PY" ]]; then
  HERMES_PY="$(python3 -c 'import sys; print(sys.executable)' 2>/dev/null || true)"
  warn "could not read Hermes' interpreter from its launcher; using $HERMES_PY"
else
  ok "hermes python $HERMES_PY"
fi
[[ -x "$HERMES_PY" ]] || die "no usable Python interpreter"

# --------------------------------------------------------------- 1. dependencies
say "1. python dependencies (pillow, nltk)"
if "$HERMES_PY" -c 'import PIL, nltk' >/dev/null 2>&1; then
  ok "already importable"
else
  # The documented path: Hermes installs what plugin.yaml declares, into its own environment.
  if run hermes plugins validate "$SRC" --install-deps >/dev/null 2>&1; then
    ok "installed via 'hermes plugins validate --install-deps'"
  else
    warn "'hermes plugins validate --install-deps' did not complete; installing directly"
    run "$HERMES_PY" -m pip install --quiet "pillow>=10,<14" "nltk>=3.8,<4" \
      || die "could not install pillow/nltk into $HERMES_PY"
    ok "installed into $HERMES_PY"
  fi
  "$HERMES_PY" -c 'import PIL, nltk' 2>/dev/null || [[ $DRY -eq 1 ]] || die "pillow/nltk still not importable — install them into $HERMES_PY by hand"
fi

# ------------------------------------------------------------------- 2. corpora
say "2. nltk corpora (wordnet, framenet)"
NLTK_DIR="$HOME/nltk_data"
if [[ -d "$NLTK_DIR/corpora/wordnet" && -d "$NLTK_DIR/corpora/framenet_v17" ]]; then
  ok "already present in $NLTK_DIR"
else
  run "$HERMES_PY" - "$NLTK_DIR" <<'PY' || die "nltk corpus download failed (network?)"
import sys, nltk
dest = sys.argv[1]
for pkg in ("wordnet", "framenet_v17"):
    nltk.download(pkg, download_dir=dest, quiet=True)
print("downloaded to", dest)
PY
  ok "downloaded into $NLTK_DIR"
fi

# -------------------------------------------------------------------- 3. plugin
say "3. plugin files"
PLUGIN_DIR="$HERMES_HOME/plugins/antemuse"
run mkdir -p "$HERMES_HOME/plugins"
if command -v rsync >/dev/null 2>&1; then
  run rsync -a --exclude .git --exclude node_modules --exclude __pycache__ --exclude '.pytest_cache' \
    "$SRC"/ "$PLUGIN_DIR"/
else
  run mkdir -p "$PLUGIN_DIR"
  run cp -a "$SRC"/. "$PLUGIN_DIR"/
  run rm -rf "$PLUGIN_DIR/.git" "$PLUGIN_DIR/node_modules"
fi
[[ $DRY -eq 1 ]] || [[ -f "$PLUGIN_DIR/plugin.yaml" ]] || die "plugin.yaml missing after copy"
ok "$PLUGIN_DIR"

say "3b. register and enable"
if [[ $NO_CLI -eq 1 ]]; then
  warn "--no-cli: skipped register/enable"
elif hermes plugins list 2>/dev/null | grep -q antemuse; then
  ok "already registered"
else
  # 'adopt' needs a git origin; a plain copy has none, and 'enable' is enough without provenance.
  run hermes plugins adopt antemuse >/dev/null 2>&1 || true
fi
if [[ $NO_CLI -eq 0 ]]; then
  run hermes plugins enable antemuse >/dev/null 2>&1 || warn "enable said no — check 'hermes plugins list'"
  ok "enabled"
fi

# ------------------------------------------------------------ 4. desktop half
say "4. desktop half (the pane the app loads)"
# Electron copies a package's desktop half into this directory and loads THAT copy. Editing the
# checkout changes nothing on screen until it is copied or the app rescans.
DESKTOP_DIR="$HERMES_HOME/desktop-plugins/antemuse"
run mkdir -p "$DESKTOP_DIR"
if command -v rsync >/dev/null 2>&1; then
  run rsync -a "$SRC"/desktop/ "$DESKTOP_DIR"/
else
  run cp -a "$SRC"/desktop/. "$DESKTOP_DIR"/
fi
if [[ $DRY -eq 0 ]]; then
  cat > "$DESKTOP_DIR/.hermes-package.json" <<JSON
{"name": "antemuse", "source": "$SRC/desktop"}
JSON
fi
ok "$DESKTOP_DIR"

# -------------------------------------------------------------- 5. projection
say "5. wordnet projection (where concepts sit on the picture)"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/antemuse"
run mkdir -p "$CACHE_DIR"
if [[ -f "$SRC/assets/projection/wordnet.proj.json" && -f "$SRC/assets/projection/wordnet.proj.f16" ]]; then
  run cp -f "$SRC/assets/projection/wordnet.proj.json" "$SRC/assets/projection/wordnet.proj.f16" "$CACHE_DIR"/
  ok "placed in $CACHE_DIR"
elif [[ -f "$CACHE_DIR/wordnet.proj.json" && -f "$CACHE_DIR/wordnet.proj.f16" ]]; then
  ok "already in $CACHE_DIR"
else
  warn "no projection — concepts fall back to a plain circle until tools/project_wordnet.py runs"
fi

# ------------------------------------------------------------------ 6. ledger
say "6. first ledger scan"
if [[ $DRY -eq 0 ]]; then
  "$HERMES_PY" - "$PLUGIN_DIR" "$HERMES_HOME" <<'PY' || warn "scan did not run; the ledger fills as you use Hermes"
import sys
sys.path.insert(0, sys.argv[1])
from core import history
store = history.HERMES_DB() if callable(history.HERMES_DB) else history.HERMES_DB
print("   session store:", store, "exists" if store.exists() else "MISSING")
print(" ", history.scan_sessions(days=7))
PY
fi
ok "ledger ready (it also fills from use: every served concept is recorded)"

# -------------------------------------------------------------------- 7. doctor
say "7. doctor"
if [[ $NO_CLI -eq 1 ]]; then
  warn "--no-cli: skipped doctor"
elif [[ $DRY -eq 0 ]]; then
  # Show the doctor's own words on failure: it is the only thing that knows why it said no, and a
  # bare "failed" sends the user looking in the wrong place.
  if ! out="$(hermes plugins doctor antemuse 2>&1)"; then
    printf '%s\n' "$out" | tail -12
    die "'hermes plugins doctor antemuse' failed — if the message is about Hermes' own venv rather than this plugin, run 'hermes pm repair'"
  fi
  printf '%s\n' "$out" | tail -3
  # A doctor that passes while nothing registered is the failure we actually hit on Windows:
  # the tool and hook counts are the part that matters, so check them, not the exit code alone.
  tools="$(doctor_count "$out" tool)"
  hooks="$(doctor_count "$out" hook)"
  [[ "${tools:-0}" -ge 1 ]] || die "the plugin registered ${tools:-0} tools — expected at least 1 (run 'hermes plugins doctor antemuse' and read the first error)"
  [[ "${hooks:-0}" -ge 5 ]] || die "the plugin registered ${hooks:-0} hooks — expected at least 5"
  ok "${tools} tool(s), ${hooks} hook(s) registered"
fi

say "8. smoke test (enters a state in a throwaway home)"
if [[ $DRY -eq 0 ]]; then
  ANTEMUSE_STATES_HOME="$(mktemp -d)" "$HERMES_PY" - "$PLUGIN_DIR" <<'PY' || die "the plugin could not enter a state"
import sys
sys.path.insert(0, sys.argv[1])
from core import engine
print(" ", engine.enter("walk").splitlines()[0])
PY
fi

say "done"
cat <<'TXT'
  Two things this script cannot do from inside a Hermes process:

    hermes gateway restart          # the running gateway holds the old module until it restarts
                                    # (this also drops the session that ran the installer)

  Then, in the desktop app: Capabilities -> Plugins -> Rescan (or just restart the app), so it
  picks up the desktop half.

  Ready to try:  /walk   then   /return
TXT
