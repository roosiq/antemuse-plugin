"""Every module the shipped code imports must exist in the package.

0.10.30 deleted ten core modules (the text/card/terminal surfaces). Two tools kept importing
them and would have died on import — `tools/bench.py` (panel, photographs, tui) and
`tools/e2e_activation.py` (screensaver). The suite never noticed because `tests/` does not
cover `tools/`, so a green run said nothing about whether the package's own scripts start.

This test closes that hole the way the packing gate does: it reads what actually ships and
resolves every `core.<name>` reference against the modules present in `core/`.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"

# Evidence and scratch trees are not runtime: they keep historical reports whose imports
# described the tree as it was when the experiment ran.
EXEMPT_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", "dist",
               "experiments", "evaluation"}


def _core_names() -> set[str]:
    names = {p.stem for p in CORE.glob("*.py")}
    names |= {p.name for p in CORE.iterdir() if p.is_dir() and (p / "__init__.py").exists()}
    names.discard("__init__")
    return names


def _shipped_py():
    for path in ROOT.rglob("*.py"):
        if EXEMPT_DIRS & set(path.relative_to(ROOT).parts):
            continue
        yield path


SHELL_SUFFIXES = {".sh", ".bash", ".zsh"}
_SHELL_IMPORT = re.compile(r"(?:from\s+core\s+import\s+([\w, ]+)|import\s+core\.(\w+))")


def _shipped_shell():
    """Scripts that run python: `bin/antemuse` was a two-line shell wrapper whose whole body was
    `python3 -c 'from core import tui'`, and tui.py was deleted in 0.10.30 with nothing watching
    the wrapper. A .py-only scan cannot see that."""
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        if EXEMPT_DIRS & set(path.relative_to(ROOT).parts):
            continue
        if path.suffix in SHELL_SUFFIXES or path.parent.name == "bin":
            yield path


def _references(tree: ast.AST):
    """`(lineno, module)` for every core.<x> the file imports."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "core" and node.level == 0:
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("core."):
            module = node.module or ""
            yield node.lineno, module.split(".", 1)[1].split(".")[0]
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("core."):
                    yield node.lineno, alias.name.split(".", 1)[1].split(".")[0]


def test_nothing_that_ships_imports_a_module_the_package_dropped():
    available = _core_names()
    offenders = []
    for path in _shipped_py():
        try:
            tree = ast.parse(path.read_text(errors="ignore"))
        except SyntaxError as exc:  # a file that cannot parse cannot run either
            offenders.append(f"{path.relative_to(ROOT)}:{exc.lineno} syntax error: {exc.msg}")
            continue
        for lineno, name in _references(tree):
            if name not in available:
                offenders.append(f"{path.relative_to(ROOT)}:{lineno} imports core.{name}")
    assert not offenders, "shipped code imports modules the package no longer has:\n" + "\n".join(
        sorted(offenders))


def test_the_scanner_sees_the_imports_that_broke_0_10_30():
    """The rule is only worth having if it fires on the shape that shipped broken."""
    dropped = ast.parse("from core import screensaver, storage\n")
    assert sorted(name for _, name in _references(dropped)) == ["screensaver", "storage"]
    assert "screensaver" not in _core_names()


def test_a_script_that_runs_python_only_imports_modules_that_exist():
    available = _core_names()
    offenders = []
    for path in _shipped_shell():
        text = path.read_text(errors="ignore")
        for match in _SHELL_IMPORT.finditer(text):
            names = [n.strip() for n in (match.group(1) or "").split(",") if n.strip()]
            if match.group(2):
                names = [match.group(2)]
            for name in names:
                if name not in available:
                    offenders.append(f"{path.relative_to(ROOT)}: runs python importing core.{name}")
    assert not offenders, "a shipped script runs python against a module the package dropped:\n" + "\n".join(sorted(offenders))
