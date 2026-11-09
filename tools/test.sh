#!/usr/bin/env bash
# One command to run the suite the way CI and reviewers do.
#
#   tools/test.sh                    # suite, temp data dir, no renderer deps
#   tools/test.sh --with-renderers   # npm ci first, so the 7 renderer tests run
#   tools/test.sh tests/test_states.py -q
#
# PYTHONPATH is dropped because the host exports it and it breaks collection.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--with-renderers" ]]; then
  shift
  npm ci --silent
fi

export ANTEMUSE_STATES_HOME="${ANTEMUSE_STATES_HOME:-$(mktemp -d)}"
exec env -u PYTHONPATH \
  uvx --with pytest --with pillow --with nltk --with pyyaml --with fastapi --quiet \
  pytest tests/ -q "$@"
