"""Deterministic text measures for idea lists.

These need no judge, so they cannot drift between raters or sessions. What they
do not do is decide whether an idea is good — perplexity is not quality, and a
low type-token ratio can be a short list rather than a repetitive one. They are
here because they are reproducible: same text, same number, every time.

  perplexity     token-level, under Qwen3-0.6B (base) held out of every condition
  surprisal      mean negative log-likelihood per token, the same thing in nats
  ttr            type-token ratio over the whole list
  mtld           measure of textual lexical diversity (length-robust TTR)
  distinct2      distinct bigrams / total bigrams
  hapax          share of word types that occur exactly once
  compression    zlib length / raw length — repetition proxy
  self_overlap   mean pairwise bigram Jaccard inside the list — how much the
                 ideas reuse each other's phrasing
"""
from __future__ import annotations

import math
import re
import zlib
from itertools import combinations

_LM = None
_TOK = None

WORD = re.compile(r"[a-z']+")


def _lm():
    global _LM, _TOK
    if _LM is None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        name = "Qwen/Qwen3-0.6B"
        _TOK = AutoTokenizer.from_pretrained(name, local_files_only=True)
        _LM = AutoModelForCausalLM.from_pretrained(name, local_files_only=True,
                                                   torch_dtype=torch.float32)
        _LM.eval()
    return _LM, _TOK


def surprisal(texts: list[str]) -> dict:
    """Mean NLL per token and the implied perplexity, per list."""
    import torch

    model, tok = _lm()
    total_nll, total_tok = 0.0, 0
    per_item = []
    with torch.no_grad():
        for t in texts:
            enc = tok(t, return_tensors="pt", truncation=True, max_length=128)
            ids = enc["input_ids"]
            if ids.shape[1] < 3:
                continue
            out = model(**enc, labels=ids)
            n = ids.shape[1] - 1
            nll = float(out.loss) * n          # loss is mean over predicted tokens
            total_nll += nll
            total_tok += n
            per_item.append(nll / n)
    if not total_tok:
        return {"surprisal": None, "ppl": None}
    mean_nll = total_nll / total_tok
    return {"surprisal": round(mean_nll, 3),
            "ppl": round(math.exp(mean_nll), 1),
            "ppl_median": round(math.exp(sorted(per_item)[len(per_item) // 2]), 1) if per_item else None}


def ttr(words: list[str]) -> float | None:
    return round(len(set(words)) / len(words), 3) if words else None


def mtld(words: list[str], threshold: float = 0.72) -> float | None:
    """Forward MTLD: mean segment length at which TTR falls to the threshold."""
    if len(words) < 50:
        return None

    def run(seq):
        factors, types, count = 0.0, set(), 0
        for w in seq:
            count += 1
            types.add(w)
            if len(types) / count <= threshold:
                factors += 1
                types, count = set(), 0
        if count:
            factors += (1 - len(types) / count) / (1 - threshold)
        return len(seq) / factors if factors else None

    f = run(words)
    b = run(list(reversed(words)))
    if f is None or b is None:
        return None
    return round((f + b) / 2, 1)


def distinct2(words: list[str]) -> float | None:
    if len(words) < 3:
        return None
    grams = list(zip(words, words[1:]))
    return round(len(set(grams)) / len(grams), 3)


def hapax(words: list[str]) -> float | None:
    if not words:
        return None
    counts: dict[str, int] = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    return round(sum(1 for v in counts.values() if v == 1) / len(counts), 3)


def compression(texts: list[str]) -> float | None:
    raw = "\n".join(texts).encode()
    if not raw:
        return None
    return round(len(zlib.compress(raw, 9)) / len(raw), 3)


def self_overlap(texts: list[str], n: int = 2, limit: int = 200) -> float | None:
    grams = []
    for t in texts:
        w = WORD.findall(t.lower())
        grams.append({tuple(w[i:i + n]) for i in range(max(0, len(w) - n + 1))})
    grams = [g for g in grams if g]
    if len(grams) < 2:
        return None
    pairs = list(combinations(range(len(grams)), 2))
    if len(pairs) > limit:
        import random
        pairs = random.Random(0).sample(pairs, limit)
    vals = []
    for i, j in pairs:
        union = grams[i] | grams[j]
        if union:
            vals.append(len(grams[i] & grams[j]) / len(union))
    return round(sum(vals) / len(vals), 4) if vals else None


def measure(ideas: list[str], with_lm: bool = True) -> dict:
    words = [w for t in ideas for w in WORD.findall(t.lower())]
    out = {"ttr": ttr(words), "mtld": mtld(words), "distinct2": distinct2(words),
           "hapax": hapax(words), "compression": compression(ideas),
           "self_overlap": self_overlap(ideas), "words": len(words)}
    out.update(surprisal(ideas) if with_lm else {"surprisal": None, "ppl": None})
    return out


def annotate(cells: list[dict]) -> None:
    for c in cells:
        if len(c.get("ideas", [])) >= 5:
            c.update({f"in_{k}": v for k, v in measure(c["ideas"]).items()})
