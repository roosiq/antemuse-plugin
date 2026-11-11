#!/usr/bin/env python3
"""DeepDream with an actual CNN over text.

Not a transformer, not token-swap search. A 1-D convolutional net whose filters
slide over contiguous word windows — the text equivalent of image patches —
trained to score text, then ascended through in embedding space:

  pixels      the input embedding matrix (V x d), one row per position
  jitter      shift the sequence by +-1 positions before each ascent step, so a
              filter cannot lock onto one offset
  octaves     grow the sequence between rounds; structure that survives the
              rescale is the motif, structure that does not is noise
  objective   mean activation of ONE chosen filter, never the class score

Because the filter slides, ascent tends to produce a *repeating* motif across
positions — the text analogue of the dog-slurry texture in the 2015 images.

Trains from any jsonl with {"text": ..., "label": 0|1}. Run with the venv that
has torch: <torch venv>/services/gateway/.venv/bin/python
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoTokenizer

BASE = "distilbert-base-uncased"
DEV = "cpu"


class TextCNN(nn.Module):
    """Kim-style CNN: n-gram filters over the embedding sequence."""

    def __init__(self, vocab: int, dim: int = 64, n_filters: int = 64,
                 widths=(3, 4, 5), dropout: float = 0.3):
        super().__init__()
        self.embed = nn.Embedding(vocab, dim, padding_idx=0)
        self.convs = nn.ModuleList(
            [nn.Conv1d(dim, n_filters, k, padding=k // 2) for k in widths]
        )
        self.drop = nn.Dropout(dropout)
        self.head = nn.Linear(n_filters * len(widths), 1)

    def features(self, ids):
        """(B, L, F) concatenated max-pooled filter activations."""
        x = self.embed(ids).transpose(1, 2)           # (B, d, L)
        outs = []
        for conv in self.convs:
            a = F.relu(conv(x))                       # (B, F, L)
            outs.append(a.max(dim=2).values)
        return torch.cat(outs, dim=1)

    def filter_maps(self, ids):
        """Per-filter activation over positions, for one sequence: list of (B,F,L)."""
        x = self.embed(ids).transpose(1, 2)
        return [F.relu(conv(x)) for conv in self.convs]

    def forward(self, ids):
        return self.head(self.drop(self.features(ids))).squeeze(-1)


def load_jsonl(path: Path, limit: int | None = None):
    rows = []
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            t = d.get("text") or ""
            if len(t) < 40:
                continue
            rows.append((t, int(d["label"])))
    random.Random(0).shuffle(rows)
    return rows[:limit] if limit else rows


def encode(tok, texts, max_len=96):
    enc = tok(list(texts), max_length=max_len, padding="max_length",
              truncation=True, return_tensors="pt")
    return enc["input_ids"]


def train(rows, tok, epochs=2, max_len=96, bs=32, lr=1e-3):
    model = TextCNN(vocab=tok.vocab_size).to(DEV)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    cut = int(len(rows) * 0.9)
    tr, va = rows[:cut], rows[cut:]
    for ep in range(epochs):
        model.train()
        random.shuffle(tr)
        total = 0.0
        for i in range(0, len(tr), bs):
            batch = tr[i:i + bs]
            ids = encode(tok, [t for t, _ in batch], max_len)
            y = torch.tensor([float(l) for _, l in batch])
            loss = F.binary_cross_entropy_with_logits(model(ids), y)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total += float(loss) * len(batch)
        model.eval()
        with torch.no_grad():
            vids = encode(tok, [t for t, _ in va], max_len)
            vy = torch.tensor([float(l) for _, l in va])
            pred = (torch.sigmoid(model(vids)) > 0.5).float()
            acc = float((pred == vy).float().mean())
        print(f"  epoch {ep+1}: train loss {total/len(tr):.4f}  val acc {acc:.3f}")
    return model


def pick_filter(model, tok, texts, width_idx=1):
    """Which filter in one conv layer fires hardest on the corpus."""
    ids = encode(tok, texts, 96)
    with torch.no_grad():
        maps = model.filter_maps(ids)[width_idx]      # (B,F,L)
    return maps.mean(dim=(0, 2))                       # (F,)


def dream(model, tok, seed_text, width_idx, filt, rounds=6, steps=40, lr=0.08,
          grow=1.6, max_len=96):
    """Jittered, octaved ascent on the input embeddings for one filter."""
    ids = encode(tok, [seed_text], max_len)[0]
    special = {tok.cls_token_id, tok.sep_token_id, tok.pad_token_id}
    seq = ids.clone()
    trail = []

    def filt_act(e):
        x = e.t().unsqueeze(0)
        return F.relu(model.convs[width_idx](x))[0, filt]

    for r in range(rounds):
        seq = grow_sequence(seq, tok, grow, max_len, special)
        emb = model.embed(seq).detach().clone()
        # dead-filter escape: nudge until the filter fires anywhere at all
        for _ in range(40):
            if float(filt_act(emb).max()) > 1e-4:
                break
            emb = emb + 0.05 * torch.randn_like(emb)

        for _ in range(steps):
            L = emb.shape[0]
            j = random.randint(0, 1)
            window = torch.arange(j, L - (1 - j)) if L > 4 else torch.arange(L)
            e = emb[window].clone().requires_grad_(True)
            a = filt_act(e)
            # maximize the strongest single activation, not the mean: a dead
            # mean gives zero gradient, a peak always has somewhere to push
            loss = -a.max()
            loss.backward()
            with torch.no_grad():
                g = e.grad
                g = g / (g.norm() + 1e-8)          # normalized step, so the
                emb[window] -= lr * g              # move is scale-free; minus
                #                                    because loss = -activation

        # project back to real tokens. Continuous -> nearest was tested and
        # silently returns the original text: the ascent saturates one window
        # while every nearest-neighbour lookup stays in its own cell. So the
        # projection is per position with acceptance: for the positions the
        # gradient moves hardest, take the nearest token to the moved
        # embedding and keep the swap only if the filter actually fires harder.
        e_full = emb.clone().requires_grad_(True)
        with torch.enable_grad():
            loss = -filt_act(e_full).max()
            loss.backward()
        with torch.no_grad():
            g = e_full.grad
            W = model.embed.weight
            Wn = W / (W.norm(dim=1, keepdim=True) + 1e-8)
            order = g.norm(dim=1).topk(min(10, g.shape[0])).indices.tolist()
            base = float(filt_act(model.embed(seq).detach()).max())
            best_seq, best_act = seq.clone(), base
            for p in order:
                # HotFlip direction: the token whose embedding best aligns with
                # the ascent gradient at this position, then verified
                direction = -g[p]
                cand_tok = int((W @ direction).argmax())
                if cand_tok in special or cand_tok == int(seq[p]):
                    continue
                trial = seq.clone()
                trial[p] = cand_tok
                act = float(filt_act(model.embed(trial).detach()).max())
                if act > best_act + 1e-6:
                    best_seq, best_act = trial, act
            seq = best_seq
            act_cur = best_act
        trail.append(act_cur)
        print(f"  round {r+1}: filter {filt} peak act {act_cur:.3f} · "
              f"{len(seq)} tok · {tok.decode(seq, skip_special_tokens=True)[:140]}")

    return tok.decode(seq, skip_special_tokens=True), trail


def grow_sequence(seq, tok, factor, max_len, special):
    """Octave: repeat content positions to a longer sequence."""
    content = [int(t) for t in seq if int(t) not in special]
    if not content:
        return seq
    target = min(max_len - 2, max(8, int(len(content) * factor)))
    out = []
    while len(out) < target:
        out.extend(content)
    out = out[:target]
    return torch.tensor([tok.cls_token_id] + out + [tok.sep_token_id])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path,
                    default=Path.home() / "toslop-model/specs/007-ai-slop-quality-model/data/train_v5.jsonl")
    ap.add_argument("--limit", type=int, default=3000)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--seed-text", default=(
        "the walk ended at a door that was also a hinge, and the hinge remembered "
        "being a river before anyone had asked it to hold anything open"))
    ap.add_argument("--width", type=int, default=1, help="0=k3 1=k4 2=k5")
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(BASE)
    rows = load_jsonl(args.data, args.limit)
    print(f"training CNN on {len(rows)} rows ({args.data.name})")
    model = train(rows, tok, epochs=args.epochs)

    print("\nfilter survey (peak activation on the seed, k=4 layer)")
    sids = encode(tok, [args.seed_text], 96)
    with torch.no_grad():
        maps = model.filter_maps(sids)[args.width][0]      # (F, L)
    peak = maps.max(dim=1).values
    top = torch.topk(peak, 3)
    for val, idx in zip(top.values.tolist(), top.indices.tolist()):
        print(f"  filter {idx:2d}  peak act {val:.3f}")

    for filt in top.indices.tolist()[:2]:
        print(f"\n=== dreaming filter {filt} (k=4) ===")
        text, trail = dream(model, tok, args.seed_text, args.width, filt)
        print(f"  final: {text}")


if __name__ == "__main__":
    main()
