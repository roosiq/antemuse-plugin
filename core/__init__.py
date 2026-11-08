"""Antemuse internals: the states, the engine that holds one, and what draws it.

  states      the five cognitive states and what each one costs
  engine      one active state per profile: enter, tick, policy, residue
  storage     where that record lives on disk
  walks       walks are data, not code: a graph plus rules for moving on it
  sources     where a state's material comes from (WordNet, FrameNet, memory, feeds)
  social      the live feeds a doomscroll eats
  ticker      the timer that delivers material while a state runs
  panel       one text frame the person can watch and take part in
  photographs the terminal image path: cells, dissolves, drift
  walk_map    the walk drawn as a side-scrolling place
  backdrop    optional pre-rendered three.js frames, replayed as blocks
  surfaces    the same frame encoded per client (terminal, chat, text, image)
  screensaver the ambient scenes: ribbons on a black field, in the ramp
  tui         the full-screen takeover
"""

from . import screensaver  # noqa: E402,F401  the ambient renderer
