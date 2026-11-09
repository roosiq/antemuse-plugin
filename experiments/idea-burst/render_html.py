"""Render idea-burst results as one page. Presentation only."""
from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABEL = {"A": "baseline", "B": "creative instruction", "D": "antemuse material"}


def esc(x) -> str:
    return html.escape(str(x))


def render_model(payload: dict) -> str:
    stats = payload["stats"]
    agg = stats["aggregate"]
    model = payload["model"]
    rows = ""
    for c in ("A", "B", "D"):
        e = agg[c]
        rows += (f"<tr><td><b>{c}</b><br><span class=muted>{esc(LABEL[c])}</span></td>"
                 f"<td>{e['ideas']}</td><td>{e['mean_pairwise']}</td>"
                 f"<td>{e['distinctiveness']}</td><td>{e['novelty']}</td>"
                 f"<td>{e['usefulness']}</td><td>{e['truncated']}</td></tr>")

    cell = next((c for c in stats["cells"]
                 if c["task"] == stats["cells"][0]["task"] and c["seed"] == payload["seeds"][0]), None)
    pair = ""
    if cell:
        a = next((c for c in stats["cells"] if c["task"] == cell["task"]
                  and c["seed"] == cell["seed"] and c["condition"] == "A"), None)
        d = next((c for c in stats["cells"] if c["task"] == cell["task"]
                  and c["seed"] == cell["seed"] and c["condition"] == "D"), None)
        if a and d:
            left = "".join(f"<li>{esc(x)}</li>" for x in a["ideas"][:12])
            right = "".join(f"<li>{esc(x)}</li>" for x in d["ideas"][:12])
            pair = (f"<div class=task><div class=muted>{esc(cell['task'])} · seed {cell['seed']} · "
                    f"first twelve ideas</div><div class=pair>"
                    f"<div class=col><div class=tag>{esc(LABEL['A'])}</div><ol>{left}</ol></div>"
                    f"<div class=col after><div class=tag>{esc(LABEL['D'])}</div><ol>{right}</ol></div>"
                    f"</div></div>")

    return f"""
<section>
  <h2>{esc(model)}</h2>
  <table>
    <thead><tr><th>condition</th><th>ideas / 50</th><th>mean pairwise</th>
    <th>distinctiveness</th><th>novelty</th><th>usefulness</th><th>truncated</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  {pair}
</section>"""


def main() -> int:
    payloads = [json.loads(p.read_text()) for p in sorted(HERE.glob("results-*.json"))]
    if not payloads:
        raise SystemExit("no results-*.json — run run.py first")
    body = "".join(render_model(p) for p in payloads if p.get("stats"))
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Idea burst — 50 ideas, with and without material</title>
<style>
 body {{ font: 16px/1.55 -apple-system, system-ui, sans-serif; margin: 0; background: #101014; color: #e8e6e3; }}
 main {{ max-width: 1040px; margin: 0 auto; padding: 40px 24px 80px; }}
 h1 {{ font-size: 30px; margin: 0 0 6px; }}
 h2 {{ font-size: 20px; margin: 40px 0 12px; border-top: 1px solid #2a2a33; padding-top: 24px; }}
 table {{ width: 100%; border-collapse: collapse; margin: 10px 0 6px; }}
 th, td {{ text-align: left; padding: 9px 10px; border-bottom: 1px solid #24242c; vertical-align: top; }}
 th {{ color: #8f8c99; font-weight: 500; font-size: 13px; }}
 .muted {{ color: #8f8c99; font-size: 13px; }}
 .pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
 .col {{ background: #17171d; border: 1px solid #24242c; border-radius: 10px; padding: 14px 16px 14px 30px; }}
 .col.after {{ border-color: #3b3559; }}
 .tag {{ font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: #9a97ff; margin-bottom: 8px; }}
 ol {{ margin: 0; padding-left: 8px; }} li {{ margin: 0 0 6px; }}
 .task {{ margin: 18px 0 30px; }}
 footer {{ margin-top: 46px; color: #8f8c99; font-size: 13px; border-top: 1px solid #2a2a33; padding-top: 18px; }}
</style></head><body><main>
<h1>50 ideas, before and after</h1>
<p class=muted>Two briefs × two seeds × three conditions. One call per cell returns a numbered
list of 50 ideas. Same model, same budget. Judged axes are a blind six-idea sample per cell.</p>
{body}
<footer>Demonstration, not a preregistered result: six cells per condition-model at most,
development briefs, and judges that are not human-validated.</footer>
</main></body></html>"""
    (HERE / "index.html").write_text(page)
    print(f"wrote {HERE / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
