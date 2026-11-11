"""Antemuse internals: the states, the engine that holds one, and the record it leaves.

  states      the five cognitive states, what each one costs and how it is spoken
  engine      one active state per profile: enter, deliver, policy, residue
  storage     where that record lives on disk
  history     the concept ledger: what was met, beside what, and when
  activation  what is firing now, derived from the ledger and never authoritative
  walks       walks are data, not code: a graph plus rules for moving on it
  sources     where a state's material comes from (WordNet, FrameNet, memory, feeds)
  social      the live feed a doomscroll eats
  report      the facts an ending hands the model, so it can say what happened
  projection  the join between the ledger and the dashboard's numbers
  settings    the few numbers a host may tune

There is one picture and it is the desktop pane: `desktop/plugin.js` draws the concept
activation graph from `/graph` in raw WebGL. The plugin keeps no second renderer — no
terminal takeover, no photo scenes, no ASCII card, no baked stills.

Nothing here reads a message body at runtime except the ledgers' own ids and hashes.
"""
