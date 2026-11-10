#!/usr/bin/env bash
# Reading the doctor's registration counts.
#
# Sourced by scripts/install.sh and tested directly (tests/test_release.py), because this line
# silently gated a good install once: `sed -n 's/.*\([0-9]*\) hook.*/\1/p'` captures ZERO digits
# — `[0-9]*` means "zero or more" — so a doctor reporting 8 hooks was read as 0, and an install
# that had worked perfectly was reported as a failure. The tools counter escaped only because its
# literal 'registrations: ' anchor left the greedy `.*` nothing to backtrack over.
#
#   doctor_count "  registrations: 1 tool(s), 8 hook(s)" hook   ->  8

doctor_count() {
  local out="$1" what="$2" hit
  hit="$(printf '%s\n' "$out" | grep -oiE "[0-9]+ ${what}" | head -1)"
  printf '%s\n' "${hit%% *}"
}
