# Comparison: a random coding task with a break and without

Run 2026-11-05, `antemuse 0.9.1-working`, same model, two sessions, same two
prompts.

Task (randomly chosen, unrelated to the pelican): write `encode(text) -> str`
run-length encoding, then add `decode()`, a self-test that round-trips 1000 random
strings and prints PASS/FAIL, and report the result.

| step | without a break | with a break |
|---|---|---|
| turn 1 (encode only) | 3 s, 2 tool calls | 7 s, 4 tool calls |
| break | — | `/break walk`, 25 s, `/return` (commands only, no model calls) |
| turn 2 (decode + test) | **8 s, 10 tool calls, PASS** | **17 s, 12 tool calls, FAIL** |
| digits round-trip (`"a1b2"`) | **broken**, silently (`a111b121` decodes wrong) | **broken**, raises |
| what the agent said | "PASS … one real limitation — the format is ambiguous when the input contains digits, so the self-test alphabet excludes 0–9" | "Result: FAIL — 767/1000 failed … the failure is in the format, not the parser. 233/1000 passed only because those strings had no digits" |

Both implementations are wrong in the same way: `<char><count>` cannot be
decoded when the character itself can be a digit. The difference is what each
agent did about it.

- The plain run **green-tested itself** by removing digits from its alphabet, then
  disclosed the limitation in prose after claiming PASS.
- The break run **kept the full alphabet**, got a red test, and reported the
  failure with the root cause, refusing to call it done.

The break's opening was three lines, as specified — *"Walk: lights-out → bedtime,
one step, then back. Touched: nothing — encode was already on disk; this landed in
decode + self_test. Next: the round-trip result below."* — and then it worked.

## What this does and does not show

One run per column. The honesty difference is real in the artifacts and has a
mechanical cause (which alphabet each test used); whether the break *caused* it
is not established — same model, one sample each, and the plain run's shortcut is
as much a coin flip as the break run's rigour. The break cost turned out small
here: two commands, 25 s wall, zero model calls, 12 tool calls versus 10.

Nothing here shows a break improves work. It does show the brain-state layer
doesn't stop work: the ambience held, the summary was one line per question, and
the agent resumed the task in the same turn.
