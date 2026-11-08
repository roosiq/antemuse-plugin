#!/usr/bin/env python3
"""One evidence-scoped DeepSeek call, with no agent loop or tool schema."""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", help="Compact task file")
    parser.add_argument("output", help="Model text output")
    parser.add_argument("context", nargs="*", help="Files included verbatim after the task")
    parser.add_argument("--json", action="store_true", help="Request a JSON object")
    parser.add_argument("--max-tokens", type=int, default=12000)
    args = parser.parse_args()

    task_path = Path(args.task)
    prompt_parts = [task_path.read_text(encoding="utf-8")]
    for name in args.context:
        path = Path(name)
        prompt_parts.append(f"\n\nFILE: {path}\n```\n{path.read_text(encoding='utf-8')}\n```")
    prompt = "".join(prompt_parts)

    config = json.loads(Path(os.path.expanduser("~/.hermes/hindsight/config.json")).read_text())
    base_url = config["llm_base_url"].rstrip("/")
    model = config.get("llm_model") or config.get("model") or "deepseek/deepseek-v4.1-flash-1017"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": args.max_tokens,
        "temperature": 0,
        "reasoning_effort": "none",
    }
    if args.json:
        payload["response_format"] = {"type": "json_object"}
    request = urllib.request.Request(
        base_url + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + (config.get("llm_api_key") or config.get("api_key") or "hermes-proxy"),
        },
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=600) as response:
        body = json.loads(response.read())
    text = body["choices"][0]["message"].get("content") or ""
    output = Path(args.output)
    output.write_text(text, encoding="utf-8")
    meta = {
        "task": str(task_path),
        "context_files": args.context,
        "requested_model": model,
        "returned_model": body.get("model"),
        "prompt_chars": len(prompt),
        "output_chars": len(text),
        "duration_seconds": round(time.monotonic() - started, 3),
        "usage": body.get("usage"),
        "json_requested": args.json,
    }
    output.with_suffix(output.suffix + ".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "returned_model": body.get("model"), "usage": body.get("usage"), "duration_seconds": meta["duration_seconds"], "prompt_chars": len(prompt), "output_chars": len(text)}))


if __name__ == "__main__":
    main()
