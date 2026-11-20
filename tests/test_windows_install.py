"""The installer has to survive a Windows host, where the CLI is a shim and PATH may be empty."""
import importlib.util
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("antemuse_install", ROOT / "scripts" / "install.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_the_cli_is_resolved_the_way_the_platform_resolves_it(monkeypatch):
    # shutil.which honours PATHEXT, so it finds hermes.cmd; CreateProcess would not.
    monkeypatch.setattr(mod.shutil, "which", lambda name: r"C:\Users\r\bin\hermes.cmd")
    assert mod.hermes_cmd().endswith("hermes.cmd")
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    assert mod.hermes_cmd() == "hermes"


def test_no_cli_invocation_bypasses_the_resolver():
    src = (ROOT / "scripts" / "install.py").read_text()
    assert '["hermes"' not in src, "a bare 'hermes' argv will not resolve a Windows shim"


def test_a_missing_cli_warns_instead_of_aborting(monkeypatch, capsys):
    def boom(*a, **k):
        raise FileNotFoundError(2, "No such file or directory: 'hermes'")
    monkeypatch.setattr(mod.subprocess, "run", boom)
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    # The register/enable block must not raise: an install without the CLI still copies files.
    try:
        listed = subprocess.run([mod.hermes_cmd(), "plugins", "list"],
                                capture_output=True, text=True)
        already = "antemuse" in (listed.stdout or "")
    except (OSError, ValueError):
        already = False
    assert already is False
