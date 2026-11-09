"""Render the before/after results as a single readable page.

Reads every results*.json written by run.py in this directory and writes index.html.
No network, no model calls: this is presentation only.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABEL = {"A": "before — baseline", "B": "control — creative instruction", "D": "after — antemuse material"}


def esc(x) -> str:
    return html.escape(str(x))


def model_of(payload: dict) -> str:
    for rec in payload["records"].values():
        return rec["model"]
    return "unknown"


def block(payload: dict) -> str:
    stats = payload["stats"]
    model = model_of(payload)
    rows = "".join(
        f"<tr><td><b>{c}</b><br><span class=muted>{esc(LABEL[c])}</span></td>"
        f"<td>{stats['per_condition'][c]['n']}</td>"
        f"<td>{stats['per_condition'][c].get('mean_words')}</td>"
        f"<td>{stats['per_condition'][c]['mean_pairwise']}</td>"
        f"<td>{stats['per_condition'][c].get('distance_to_baseline')}</td></tr>"
        for c in ("A", "B", "D"))
    wins = "".join(
        f"<li><b>{esc(k)}</b>: {v['wins']}/{v['n']} consistent "
        f"({v['rate']})</li>" for k, v in stats["winrates"].items())

    examples = []
    keys = [k for k in payload["records"] if k.endswith("|11")]
    for k in keys:
        task, cond, seed = k.split("|")
        if cond not in ("A", "D"):
            continue
        rec = payload["records"][k]
        text = rec["candidates"][0]["text"] if rec["candidates"] else "(no output)"
        examples.append((task, cond, text))
    seen = {}
    for task, cond, text in examples:
        seen.setdefault(task, {})[cond] = text
    blocks = ""
    for task, pair in seen.items():
        blocks += f"<div class=task><div class=muted>{esc(task)}</div><div class=pair>"
        for cond in ("A", "D"):
            blocks += (f"<div class=col><div class=tag>{esc(LABEL[cond])}</div>"
                       f"<p>{esc(pair.get(cond, '(missing)'))}</p></div>")
        blocks += "</div></div>"

    return f"""
<section>
  <h2>{esc(model)}</h2>
  <table>
    <thead><tr><th>condition</th><th>n</th><th>mean words</th><th>mean pairwise distance</th>
    <th>distance to baseline</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <h3>Blind pairwise — both orders, two judge families</h3>
  <ul>{wins}</ul>
  <p class=muted>Order-inconsistent decisions excluded: {stats['positional_pairs']}/{stats['n_pairs']}.</p>
  <h3>Same brief, same seed</h3>
  {blocks}
</section>"""


def main() -> int:
    payloads = [json.loads(p.read_text()) for p in sorted(HERE.glob("results*.json"))]
    if not payloads:
        raise SystemExit("no results*.json found — run run.py first")
    body = "".join(block(p) for p in payloads)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Antemuse — before / after</title>
<style>
 body {{ font: 16px/1.55 -apple-system, system-ui, sans-serif; margin: 0; background: #101014; color: #e8e6e3; }}
 main {{ max-width: 1040px; margin: 0 auto; padding: 40px 24px 80px; }}
 h1 {{ font-size: 30px; margin: 0 0 6px; }}
 h2 {{ font-size: 20px; margin: 40px 0 12px; border-top: 1px solid #2a2a33; padding-top: 24px; }}
 h3 {{ font-size: 15px; text-transform: uppercase; letter-spacing: .08em; color: #9a97ff; margin: 26px 0 8px; }}
 table {{ width: 100%; border-collapse: collapse; margin: 10px 0 6px; }}
 th, td {{ text-align: left; padding: 9px 10px; border-bottom: 1px solid #24242c; vertical-align: top; }}
 th {{ color: #8f8c99; font-weight: 500; font-size: 13px; }}
 .muted {{ color: #8f8c99; font-size: 13px; }}
 .pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
 .col {{ background: #17171d; border: 1px solid #24242c; border-radius: 10px; padding: 14px 16px; }}
 .col.after {{ border-color: #3b3559; }}
 .tag {{ font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: #9a97ff; margin-bottom: 8px; }}
 .task {{ margin: 18px 0 30px; }}
 footer {{ margin-top: 46px; color: #8f8c99; font-size: 13px; border-top: 1px solid #2a2a33; padding-top: 18px; }}
 ul {{ padding-left: 20px; }}
</style></head>
<body><main>
<h1>Antemuse — before / after</h1>
<p class=muted>Two development tasks × three seeds × three conditions. Same model, same token budget.
Baseline vs a creativity instruction vs the plugin's deterministic collider material.</p>
{body}
<footer>
Demonstration only: six outputs per condition per model, development tasks, and judges that are
order-controlled but not human-validated. The preregistered state experiment under
<code>experiments/state-settings/</code> remains the evidence path.
</footer>
</main></body></html>"""
    (HERE / "index.html").write_text(page)
    print(f"wrote {HERE / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
