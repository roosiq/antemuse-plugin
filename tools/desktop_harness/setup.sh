#!/usr/bin/env bash
# Wire the harness to the Hermes desktop checkout's node_modules.
#
# The harness runs the real desktop/plugin.js, which imports 'react',
# 'react-dom/server' and '@hermes/plugin-sdk'. The first two exist in the app
# checkout; the third is stubbed here. Nothing is installed and nothing is
# written outside this directory except the node_modules/bin links below.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
host="${HERMES_APP_NODE_MODULES:-/home/ryan/.hermes/hermes-agent/node_modules}"

mkdir -p "$here/node_modules/@hermes/plugin-sdk" "$here/.work"

for pkg in react react-dom jsdom; do
  if [ ! -d "$host/$pkg" ]; then
    echo "missing $host/$pkg — set HERMES_APP_NODE_MODULES to the desktop checkout's node_modules" >&2
    exit 1
  fi
  ln -sfn "$host/$pkg" "$here/node_modules/$pkg"
done

printf '{"name":"@hermes/plugin-sdk","type":"module","exports":"./index.js"}\n' \
  > "$here/node_modules/@hermes/plugin-sdk/package.json"
printf "export * from '../../../sdk-stub.js'\n" \
  > "$here/node_modules/@hermes/plugin-sdk/index.js"

echo "harness ready: $(readlink -f "$here/node_modules/react")"
