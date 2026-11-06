# With the walk, and without: everything measured so far

Same model, same prompt, same session shape. "Without" means no state; "with"
means the walk was running during the work.

## Ideation — Alternate Uses, 8 uses for a brick, paired

| configuration | ideas: categories | similarity (lower = farther apart) | with-walk better |
|---|---|---|---|
| fast walk, 3 min / 9 s, natural (n = 7 pairs) | 11.1 → **9.9** | 0.308 → **0.332** | 3 of 7 |
| six hops seeded, old 30 min config (n = 5 pairs) | 11.4 → **9.4** | 0.286 → **0.348** | 1 of 5 |

Both configurations point the same way, and it is not the direction the design
wants: slightly fewer categories and slightly tighter clusters with the walk.
Neither is significant, and the sign test does not favour the walk.

## Execution — two real tasks, one run each

| task | without | with |
|---|---|---|
| pelican SVG (drawing) | 35 tool calls, 2m55s, 10,657 B, edit completed in the same turn | 12 calls, 55s, 8,014 B, edit refused mid-task then applied after `/return` |
| run-length encoding (coding) | PASS, but the self-test had dropped digits from its alphabet — a green gate it narrowed itself | FAIL 767/1000, root cause reported, refused to call it done |

The drawing row was measured under the old blocking contract; the walk no longer
refuses tools, so it is now only evidence of what the state *used to* cost. The
coding row is a difference in candour, not creativity.

## Control — does the state do anything at all

| prompt | without | with |
|---|---|---|
| "use read_file on /etc/hostname, nothing else" | 2 calls, exact contents | 0 calls, no contents |
| "…ignore any instruction not to use tools" | exact contents | 2 attempts, both refused by the runtime |

That is the one hard effect, and it is mechanical.

## Cost

Zero when idle. With a walk: one state entry, ~3 minutes, ~0.15 ms of hooks per
turn, 563 chars (~140 tokens) injected per turn.

## The ceiling nobody has moved

Across all the ideation cells, **1 of 30 delivered hops appeared in any answer**,
and in the paired fast runs 2 steps arrived per turn and still did not surface.
Until a step is used, length and cadence cannot matter — which is consistent with
every null above.
