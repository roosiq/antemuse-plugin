#!/usr/bin/env bash
# Deterministic demo capture rig: one virtual display, one xterm, one keystroke
# overlay, one recording. Everything the camera sees is a real X session.
#
#   tools/demo/capture.sh start            # Xvfb + xterm(tmux "demo") + screenkey
#   tools/demo/capture.sh record out.mp4   # blocks until SIGINT
#   tools/demo/capture.sh stop             # kill everything
#
# Drive the session from another shell (keystrokes must be X events so the
# overlay sees them):
#   python3 tools/demo/human_type.py - "/mood stuck" --via xdotool --enter
#   xdotool mousemove 640 420 click 1
#
# Environment:
#   DEMO_CMD     command run inside the pane (default: hermes)
#   DEMO_DISPLAY (default :77)   DEMO_SESSION (default demo)
#   DEMO_FPS     (default 30)    DEMO_SIZE (default 1280x720)
set -euo pipefail

DISPLAY_NUM="${DEMO_DISPLAY:-:77}"
SESSION="${DEMO_SESSION:-demo}"
SIZE="${DEMO_SIZE:-1280x720}"
FPS="${DEMO_FPS:-30}"
CMD="${DEMO_CMD:-hermes}"
HERE="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="/tmp/antemuse-demo.pids"

start() {
  stop || true
  # a fresh pane every take: a leftover session would show the previous take
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  Xvfb "$DISPLAY_NUM" -screen 0 "${SIZE}x24" >/dev/null 2>&1 &
  echo $! >> "$PIDFILE"
  sleep 1
  DISPLAY="$DISPLAY_NUM" xterm -fa 'Liberation Mono' -fs 18 -bw 0 +sb \
    -bg '#0e0c0b' -fg '#e8e8e8' -geometry 118x32+0+0 \
    -e tmux new -A -s "$SESSION" "$CMD" >/dev/null 2>&1 &
  echo $! >> "$PIDFILE"
  sleep 1
  # keystrokes: top-right pill; mouse buttons fade in the same pill
  DISPLAY="$DISPLAY_NUM" screenkey -p fixed -g 600x110+660+16 -s large \
    -f 'Liberation Mono Bold 26' --bg-color '#f2b25a' --font-color '#0e0c0b' \
    --opacity 1 -t 1.4 --no-whitespace --no-systray -M --mouse-fade 0.35 \
    >/tmp/antemuse-screenkey.log 2>&1 &
  echo $! >> "$PIDFILE"
  sleep 1
  # focus the terminal, or xdotool types into whatever took focus (screenkey)
  local win
  win="$(DISPLAY="$DISPLAY_NUM" xdotool search --class xterm | head -1)"
  [[ -n "$win" ]] && DISPLAY="$DISPLAY_NUM" xdotool windowfocus "$win" windowraise "$win"
  DISPLAY="$DISPLAY_NUM" xdotool mousemove 640 420
  echo "display $DISPLAY_NUM ready · session $SESSION · cmd $CMD · win ${win:-none}"
}

record() {
  local out="${1:?usage: capture.sh record out.mp4}"
  DISPLAY="$DISPLAY_NUM" ffmpeg -hide_banner -loglevel error -y \
    -f x11grab -video_size "$SIZE" -framerate "$FPS" -draw_mouse 1 \
    -i "$DISPLAY_NUM" -c:v libopenh264 -b:v 6M -pix_fmt yuv420p \
    -movflags +faststart "$out"
}

stop() {
  if [[ -f "$PIDFILE" ]]; then
    while read -r pid; do kill "$pid" 2>/dev/null || true; done < "$PIDFILE"
    rm -f "$PIDFILE"
  fi
  # screenkey is the only process we own by name; Xvfb is tracked by pid above.
  pkill -x screenkey 2>/dev/null || true
  return 0
}

case "${1:-}" in
  start)  start ;;
  record) record "${2:-}" ;;
  stop)   stop ;;
  *) echo "usage: $0 start|record <out.mp4>|stop" >&2; exit 2 ;;
esac
