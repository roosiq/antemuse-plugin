#!/usr/bin/env python3
"""Render `docs/architecture.md` as a single self-contained page.

The page is generated from the markdown rather than hand-written, because a website
that restates an architecture doc is a second copy that will drift. Run this after
editing the doc; `site/index.html` is committed as the built artifact.

    python3 tools/site.py            # writes site/index.html
"""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs/architecture.md"
OUT = ROOT / "site/index.html"

STATUS_CLASS = {
    "LIVE": "live",
    "PARTIAL": "partial",
    "PROPOSED": "proposed",
    "NOT BUILT": "unbuilt",
}

CSS = """
:root{
  --bg:#06070a; --panel:#0b0e13; --line:#1d232c; --ink:#d7dde4; --dim:#8c97a3;
  --live:#4fe0b0; --partial:#e8b54a; --proposed:#9d8cf0; --unbuilt:#7c6f6f;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.62 ui-monospace,SFMono-Regular,Menlo,monospace;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1080px;margin:0 auto;padding:64px 28px 96px}
.grain{
  position:fixed;inset:0;pointer-events:none;z-index:0;
  background:radial-gradient(ellipse at 50% -10%,#1118238c 0%,transparent 60%);
}
h1{font-size:30px;line-height:1.2;margin:0 0 10px;letter-spacing:-.01em}
h2{font-size:19px;margin:56px 0 14px;padding-top:18px;border-top:1px solid var(--line)}
h3{font-size:15px;margin:28px 0 10px;color:var(--dim);text-transform:uppercase;letter-spacing:.08em}
p{margin:0 0 14px;max-width:78ch}
a{color:#7fd4ff}
code{background:#12171f;border:1px solid var(--line);border-radius:4px;padding:1px 5px;font-size:13px}
pre{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:18px 20px;
    overflow-x:auto;font-size:12.5px;line-height:1.5;color:#a9b6c4}
pre code{background:none;border:0;padding:0;font-size:inherit}
table{width:100%;border-collapse:collapse;margin:18px 0 26px;font-size:13.5px}
th{text-align:left;color:var(--dim);font-weight:500;text-transform:uppercase;font-size:11px;
   letter-spacing:.09em;padding:0 12px 8px 0;border-bottom:1px solid var(--line)}
td{padding:9px 12px 9px 0;border-bottom:1px solid #141a22;vertical-align:top}
tr:last-child td{border-bottom:0}
.chip{display:inline-block;padding:1px 7px;border-radius:3px;font-size:11px;letter-spacing:.06em;
      border:1px solid currentColor;white-space:nowrap}
.chip.live{color:var(--live)} .chip.partial{color:var(--partial)}
.chip.proposed{color:var(--proposed)} .chip.unbuilt{color:var(--unbuilt)}
.lead{color:var(--dim);max-width:70ch;margin-bottom:34px}
ul{margin:0 0 16px;padding-left:20px} li{margin:0 0 7px}
hr{border:0;border-top:1px solid var(--line);margin:40px 0}
.foot{margin-top:70px;color:var(--dim);font-size:12px}
.top{position:sticky;top:0;z-index:2;background:#06070aee;backdrop-filter:blur(8px);
     border-bottom:1px solid var(--line)}
.wrap2{max-width:1080px;margin:0 auto;padding:12px 28px;display:flex;gap:16px;
       align-items:center;flex-wrap:wrap;font-size:12.5px}
.wrap2 strong{letter-spacing:.14em;text-transform:uppercase;font-size:11px;color:var(--dim)}
.board{display:flex;gap:8px;flex-wrap:wrap}
details{margin-left:auto;color:var(--dim)}
summary{cursor:pointer}
nav{display:flex;flex-wrap:wrap;gap:4px 10px;max-width:520px;margin-top:8px;font-size:12px}
h2{scroll-margin-top:64px}
"""


def inline(text: str) -> str:
    """Inline markdown → html, escaping first so a stray < cannot become markup."""
    out = html.escape(text)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    return out


def status_chip(text: str) -> str:
    for word, cls in STATUS_CLASS.items():
        if word in text.upper():
            return f'<span class="chip {cls}">{word}</span>'
    return inline(text)


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def render_table(rows: list[str]) -> str:
    header = cells(rows[0])
    body = [cells(r) for r in rows[2:]]
    out = ["<table><thead><tr>"] + [f"<th>{inline(h)}</th>" for h in header] + ["</tr></thead><tbody>"]
    for row in body:
        row = row + [""] * (len(header) - len(row))
        tds = []
        for i, cell in enumerate(row[: len(header)]):
            # a status column is chipped, everything else is plain inline markdown
            body_cell = status_chip(cell) if any(w in cell.upper() for w in STATUS_CLASS) else inline(cell)
            tds.append(f"<td>{body_cell}</td>")
        out.append("<tr>" + "".join(tds) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def convert(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            j = i + 1
            block = []
            while j < len(lines) and not lines[j].strip().startswith("```"):
                block.append(lines[j])
                j += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(block))}</code></pre>")
            i = j + 1
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].strip()) <= set("|-: "):
            j = i
            rows = []
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(lines[j])
                j += 1
            out.append(render_table(rows))
            i = j
            continue

        if stripped.startswith("# "):
            out.append(f"<h1>{inline(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            out.append(f"<h2>{inline(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            out.append(f"<h3>{inline(stripped[4:])}</h3>")
        elif stripped.startswith("---"):
            out.append("<hr>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            j = i
            items = []
            while j < len(lines) and lines[j].strip()[:2] in ("- ", "* "):
                items.append(f"<li>{inline(lines[j].strip()[2:])}</li>")
                j += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            i = j
            continue
        elif re.match(r"^\d+\.\s", stripped):
            j = i
            items = []
            while j < len(lines) and re.match(r"^\d+\.\s", lines[j].strip()):
                items.append(f"<li>{inline(re.sub(r'^\d+\.\s', '', lines[j].strip()))}</li>")
                j += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            i = j
            continue
        elif stripped:
            out.append(f"<p>{inline(stripped)}</p>")
        i += 1
    return "\n".join(out)


def build() -> str:
    md = SRC.read_text()
    body = convert(md)

    # counts are derived from the rendered page, never typed: a summary that can
    # disagree with the table under it is worse than no summary
    counts = {word: body.count(f'class="chip {cls}"') for word, cls in STATUS_CLASS.items()}
    nav = " · ".join(
        f'<a href="#{re.sub(r"[^a-z0-9]+", "-", h.lower()).strip("-")}">{h}</a>'
        for h in re.findall(r"^## (.+)$", md, re.M)
    )
    board = " ".join(
        f'<span class="chip {STATUS_CLASS[w].lower()}">{w} {counts[w]}</span>'
        for w in STATUS_CLASS if counts[w]
    )
    page = f"""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Antemuse — architecture and status</title>
<style>{CSS}</style>
<div class="grain"></div>
<header class="top">
  <div class="wrap2">
    <strong>antemuse</strong>
    <span class="board">{board}</span>
    <details><summary>sections</summary><nav>{nav}</nav></details>
  </div>
</header>
<div class="wrap">
{body}
<p class="foot">Generated from <code>docs/architecture.md</code> by <code>tools/site.py</code>.
Edit the document, then rebuild — never the other way round.</p>
</div>
"""
    return page


def main() -> None:
    page = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page)
    print(f"{OUT} — {len(page) // 1024} KB, {page.count('<h2>')} sections, {page.count('<table>')} tables")


if __name__ == "__main__":
    main()
