#!/usr/bin/env python3
"""A pilot: run conditions A–F once against a real endpoint and show what came back.

This is not an evaluation. One task, one seed, no judge, no protected set, no
claim about quality — it exists to prove the six conditions produce six genuinely
different request shapes and real model text through the offline runner.

  env -u PYTHONPATH python3 tools/pilot.py --model liquid/lfm-3-1.7b --seed 7

Nothing is written to a frozen shard; results land in the directory you pass with
--out (a temp dir by default) so a pilot can never be mistaken for evidence.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN))

from evaluation import run as runner  # noqa: E402

CONDITION_ORDER = ("A", "B", "C", "D", "E", "F")


def transport_for(model: str, endpoint: str, *, timeout: float = 120.0,
                  max_tokens: int = 900):
    def transport(request):
        prompt = [request["instruction"]]
        for block in request.get("inputs") or []:
            if block.get("type") == "text":
                prompt.append(str(block.get("text") or ""))
        if request.get("material"):
            prompt.append(str(request["material"]))
        prompt.append("Task: " + str(request.get("brief") or ""))

        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": "\n\n".join(prompt)}],
            "temperature": 0.7,
            "seed": int(request.get("seed") or 0),
            "max_tokens": max_tokens,
        }).encode("utf-8")
        http = urllib.request.Request(
            endpoint.rstrip("/") + "/chat/completions",
            data=body, headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(http, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code}: {exc.read()[:200]!r}") from None
        choice = (payload.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            # Never coerce a null answer into the string "None": the runner would
            # record it as a successful cell and the grid would lie.
            raise RuntimeError(f"empty content (finish_reason={choice.get('finish_reason')!r})")
        usage = payload.get("usage") or {}
        return {"text": content,
                # Why it stopped, verbatim. A cell cut off at the ceiling is
                # still recorded — but as truncated, not as a finished answer.
                "finish_reason": choice.get("finish_reason"),
                "usage": {"input_tokens": usage.get("prompt_tokens"),
                          "output_tokens": usage.get("completion_tokens")}}

    return transport


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="liquid/lfm-3-1.7b")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8645/v1")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--task", default="0", help="index into the development fixture")
    parser.add_argument("--out", default="")
    parser.add_argument("--conditions", default=",".join(CONDITION_ORDER))
    parser.add_argument("--max-tokens", type=int, default=900)
    args = parser.parse_args(argv)

    fixture = json.loads((PLUGIN / "evaluation" / "tasks" / "development.json").read_text())
    tasks = fixture["tasks"]
    task = tasks[int(args.task) % len(tasks)]

    out_dir = Path(args.out or tempfile.mkdtemp(prefix="antemuse-pilot-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    transport = transport_for(args.model, args.endpoint, max_tokens=args.max_tokens)

    print(f"pilot · model {args.model} · seed {args.seed} · out {out_dir}")
    print(f"task {task['id']}: {task['brief'][:100]}…\n")

    records = []
    for condition in [c.strip() for c in args.conditions.split(",") if c.strip()]:
        record = runner.run_condition(
            condition, task,
            model=args.model,
            prompt_version="pilot-1",
            source_version="collider-6ed948a",
            seed=args.seed,
            transport=transport,
            cache_path=out_dir / "pilot-cache.jsonl",
            selector=None,
        )
        records.append(record)
        usage = record.get("usage") or {}
        chosen = record.get("selected_candidate_id")
        text = ""
        for candidate in record.get("candidates") or []:
            if candidate.get("candidate_id") == chosen:
                text = str(candidate.get("text") or "")
        synthesis = record.get("synthesis") or {}
        if synthesis.get("status") == "ok" and synthesis.get("text"):
            text = str(synthesis["text"])
        if not text and record.get("candidates"):
            text = str(record["candidates"][0].get("text") or "")
        print(f"{condition}: {record['status']:<8} calls={record['transport_calls']} "
              f"candidates={len(record.get('candidates') or [])} "
              f"selected={chosen} tokens={usage.get('output_tokens')}")
        if record.get("sources"):
            print(f"   sources: {', '.join(record['sources'])}")
        print(f"   {text.strip().replace(chr(10), ' ')[:220]}…")
        (out_dir / f"{condition}.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"\nrecords written to {out_dir} (a pilot directory, not a shard)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
