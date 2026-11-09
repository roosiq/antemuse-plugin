"""Render idea-states results as one page. Presentation only."""
from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABEL = {"N": "straight", "walk": "walk in the middle", "daydream": "daydream in the middle",
         "doomscroll": "doomscroll in the middle"}


def esc(x) -> str:
    return html.escape(str(x))


def section(payload: dict) -> str:
    stats = payload["stats"]
    agg = stats["aggregate"]
    model = payload["model"]
    rows = ""
    for c in ("N", "walk", "daydream", "doomscroll"):
        e = agg[c]
        rows += (f"<tr><td><b>{c}</b><br><span class=muted>{esc(LABEL[c])}</span></td>"
                 f"<td>{e['ideas']}</td><td>{e['mean_pairwise']}</td><td>{e['distinctiveness']}</td>"
                 f"<td>{e['novelty']}</td><td>{e['usefulness']}</td><td>{e['state_words']}</td></tr>")

    task = stats["cells"][0]["task"]
    seed = payload["seeds"][0]
    cells = {c["condition"]: c for c in stats["cells"]
             if c["task"] == task and c["seed"] == seed}
    state_notes = ""
    for cond in ("walk", "daydream", "doomscroll"):
        c = cells.get(cond)
        if c and c["state_text"]:
            state_notes += (f"<div class=note><div class=tag>{esc(LABEL[cond])}</div>"
                            f"<p>{esc(c['state_text'][:600])}</p></div>")

    lists = ""
    for cond in ("N", "daydream"):
        c = cells.get(cond)
        if c:
            items = "".join(f"<li>{esc(x)}</li>" for x in c["ideas"][:8])
            lists += (f"<div class=col{' after' if cond != 'N' else ''}>"
                      f"<div class=tag>{esc(LABEL[cond])}</div><ol>{items}</ol></div>")

    return f"""
<section>
  <h2>{esc(model)}</h2>
  <table>
    <thead><tr><th>condition</th><th>ideas / 50</th><th>mean pairwise</th><th>distinctiveness</th>
    <th>novelty</th><th>usefulness</th><th>state turn (words)</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <h3>The middle turn</h3>
  {state_notes}
  <h3>What the list looks like</h3>
  <div class=task><div class=muted>{esc(task)} · seed {seed} · first eight ideas</div>
  <div class=pair>{lists}</div></div>
</section>"""


def main() -> int:
    payloads = [json.loads(p.read_text()) for p in sorted(HERE.glob("results-*.json"))]
    if not payloads:
        raise SystemExit("no results-*.json — run run.py first")
    body = "".join(section(p) for p in payloads if p.get("stats"))
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>50 ideas, straight vs with a state in the middle</title>
<style>
 body {{ font: 16px/1.55 -apple-system, system-ui, sans-serif; margin: 0; background: #101014; color: #e8e6e3; }}
 main {{ max-width: 1040px; margin: 0 auto; padding: 40px 24px 80px; }}
 h1 {{ font-size: 30px; margin: 0 0 6px; }}
 h2 {{ font-size: 20px; margin: 40px 0 12px; border-top: 1px solid #2a2a33; padding-top: 24px; }}
 h3 {{ font-size: 13px; text-transform: uppercase; letter-spacing: .08em; color: #9a97ff; margin: 26px 0 8px; }}
 table {{ width: 100%; border-collapse: collapse; margin: 10px 0 6px; }}
 th, td {{ text-align: left; padding: 9px 10px; border-bottom: 1px solid #24242c; vertical-align: top; }}
 th {{ color: #8f8c99; font-weight: 500; font-size: 13px; }}
 .muted {{ color: #8f8c99; font-size: 13px; }}
 .pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
 .col, .note {{ background: #17171d; border: 1px solid #24242c; border-radius: 10px; padding: 14px 16px 14px 28px; }}
 .col.after {{ border-color: #3b3559; }}
 .note {{ margin: 10px 0; padding-left: 16px; }}
 .tag {{ font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: #9a97ff; margin-bottom: 8px; }}
 .note p {{ margin: 0; color: #cfccc7; font-size: 14px; }}
 ol {{ margin: 0; padding-left: 8px; }} li {{ margin: 0 0 6px; }}
 .task {{ margin: 18px 0 30px; }}
 footer {{ margin-top: 46px; color: #8f8c99; font-size: 13px; border-top: 1px solid #2a2a33; padding-top: 18px; }}
</style></head><body><main>
<h1>50 ideas, twice</h1>
<p class=muted>Two briefs × two seeds × four conditions. The model asks for the same list twice:
straight, and with a state held in the middle. State directives are read from
<code>core/states.py</code>; doomscroll's feed from <code>core/sources.feed_pick</code>.</p>
{body}
<footer>Demonstration, not a preregistered result. Four cells per condition per model, two
development briefs, judges not human-validated.</footer>
</main></body></html>"""
    (HERE / "index.html").write_text(page)
    print(f"wrote {HERE / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
