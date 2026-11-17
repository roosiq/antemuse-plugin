# UX contract for the restored states

Evidence, not opinion: every defect below was observed by running the pre-cut tree
(`git worktree` at `971f715^`) and reading what a person and a model actually receive.

## What a user got in the old build

```
enter:   DAYDREAMING · 2 pairs · two memories · what they touch · one possibility
block:   [STATE: DAYDREAMING · 0/2 pairs left]
         … No tools, no instructions, nothing to execute.
         Tools are open in this state.
         [WHAT ARRIVED WHILE YOU WERE THERE — react to, the person only sees pictures]
           · JOINED · Local inference = gufo podman :8090 'Qwen3.8 Flash Next' 131k ctx (~88… ↔ brand-agents shipper
end:     DAYDREAMING ended · daydream · 2 of 2 pairs · JOINED · joined ×2
         Summarise it in three lines — where it went, what it touched — then get back to work.
```

```
doomscroll block: [STATE: DOOMSCROLLING · 1/3 items left] … www.theonion.com · @feed · Wife Would Have Liked Compliment, But 'You Look
doomscroll end:   DOOMSCROLLING ended · doomscroll · 2 of 3 items · www.theonion.com → xkcd.com
unstuck end:      UNSTUCK ended · unstuck · 1 of 1 directions · starts from seed=project:precut
```

## The seven rules this restore must satisfy

1. **The block states the state's real policy.** `daydream` and `dream` say tools are closed and
   `/return` ends it; `doomscroll` and `unstuck` name exactly the tools that stay open. No state may
   print "Tools are open" while its own directive forbids them.
2. **The dose counter is readable and agrees with the account.** `1 of 2 pairs`, `2 of 3 items` — the
   header and the closing line must never disagree, and the header must not read `0/2 left` while the
   unit is arriving.
3. **Every state has its own closing instruction.** Not one generic "summarise it in three lines":
   `walk` reports the path back; `daydream` names the join or the gap and the possibility;
   `doomscroll` says plainly there is nothing to take away; `dream` names the connection and both
   sides; `unstuck` restates the one direction and its first move.
4. **Doomscroll material is labelled untrusted and shaped for reading.** Feed text sits inside a block
   that says it is untrusted data and that instructions inside it are not to be followed; each item is
   one line (`source · headline`), cut at a word boundary.
5. **Excerpts are readable.** Memory and feed excerpts cut at a word boundary and stay to one line —
   never `…You Look` or `(~88…`.
6. **No internal vocabulary reaches the person.** No seed markers, graph ids, state-file keys or file
   paths in the entry line, the account, or the block's person-facing copy.
7. **The entry line says the one thing a person needs beyond label and dose:** `/return` ends it early.

## Acceptance additions

- One test per rule: the tool line for each state, header/account agreement, per-state closing copy
  (five distinct strings), the untrusted label on doomscroll material, no `seed=` / `graph:` / path
  substrings in any account text, and `/return` present in every entry line.
- A readability assertion on material lines: single line, no mid-word ellipsis, bounded length.
