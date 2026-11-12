"""Settings: declared in the manifest, rendered by the host, clamped by the plugin."""
from __future__ import annotations

import os
import sys
import tempfile

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("NLTK_DATA", os.path.expanduser("~/nltk_data"))
os.environ.setdefault("ANTEMUSE_STATES_HOME", tempfile.mkdtemp(prefix="settings-test-"))

from core import settings  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Host:
    """Stands in for PluginContext: get_config reads plugins.entries.<id>.settings.<key>."""

    def __init__(self, values=None):
        self.values = values or {}

    def get_config(self, key, default=None):
        return self.values.get(key, default)


def test_the_manifest_declares_every_setting_the_plugin_reads():
    manifest = yaml.safe_load(open(os.path.join(ROOT, "plugin.yaml")))
    schema = manifest.get("config_schema") or {}
    assert set(schema) == (set(settings.BOOL_DEFAULTS) | set(settings.INT_BOUNDS)
                           | set(settings.TEXT_DEFAULTS))
    for key, spec in schema.items():
        assert spec.get("type") in ("bool", "int", "str", "string", "float"), (key, spec)
        assert "default" in spec and spec.get("label") and spec.get("description")


def test_every_declared_setting_has_a_label_a_person_can_read():
    manifest = yaml.safe_load(open(os.path.join(ROOT, "plugin.yaml")))
    for key, spec in (manifest.get("config_schema") or {}).items():
        label = spec["label"]
        assert label[0].isupper(), key
        assert "_" not in label, f"{key} label is a config key, not a sentence"


def test_defaults_when_nothing_is_configured():
    settings.bind(Host())
    assert settings.flag("recommend_enabled") is True
    assert settings.flag("suggest_autofollow") is False
    assert settings.number("recommend_cooling_turns") == 10
    assert settings.number("long_stretch_turns") == 0
    assert settings.number("journal_cap") == 60


def test_values_are_read_from_the_host_not_a_file():
    settings.bind(Host({"recommend_enabled": False, "journal_cap": 25}))
    assert settings.flag("recommend_enabled") is False
    assert settings.number("journal_cap") == 25


def test_out_of_range_is_clamped_and_never_raises():
    settings.reset_warnings()
    settings.bind(Host({"recommend_cooling_turns": 1, "journal_cap": 900,
                        "long_stretch_turns": 9999}))
    assert settings.number("recommend_cooling_turns") == 2
    assert settings.number("journal_cap") == 60, "the journal cap may only be reduced"
    assert settings.number("long_stretch_turns") == 200


def test_a_stretch_override_below_30_minutes_is_not_a_stretch():
    settings.reset_warnings()
    settings.bind(Host({"long_stretch_turns": 3}))
    assert settings.number("long_stretch_turns") == 5


def test_a_wrong_type_falls_back_to_the_default():
    settings.bind(Host({"journal_cap": "lots", "recommend_enabled": []}))
    assert settings.number("journal_cap") == 60
    assert settings.flag("recommend_enabled") is True


def test_strings_from_a_config_editor_count_as_booleans():
    settings.bind(Host({"recommend_enabled": "false", "suggest_autofollow": "YES"}))
    assert settings.flag("recommend_enabled") is False
    assert settings.flag("suggest_autofollow") is True


def test_disabled_recommendations_say_nothing(monkeypatch):
    from core import recommend
    settings.bind(Host({"recommend_enabled": False, "show_recommendations": True}))
    assert recommend.suggest({"work": {"turns": 999, "streak": 9}}) is None
    settings.bind(Host({"show_recommendations": True}))
    assert recommend.suggest({"work": {"turns": 999, "streak": 9}}) is not None


def test_hidden_recommendations_say_nothing_even_when_measured(monkeypatch):
    """Measuring a state is not the same as telling someone about it."""
    from core import recommend
    settings.bind(Host({"recommend_enabled": True}))
    assert settings.flag("show_recommendations") is False
    assert recommend.suggest({"work": {"turns": 999, "streak": 9}}) is None


def test_the_cooling_window_comes_from_settings():
    from core import mood
    import time
    settings.bind(Host({"recommend_cooling_turns": 10}))
    view = mood.view({"turns": 1, "started_at": time.time()}, [], [], since_offer=11)
    assert view["cooling"] is False
    view = mood.view({"turns": 1, "started_at": time.time()}, [], [], since_offer=5)
    assert view["cooling"] is True


def test_no_host_means_defaults_and_no_crash():
    settings.bind(None)
    assert settings.flag("recommend_enabled") is True
    assert settings.flag("suggest_autofollow") is False
    assert settings.number("journal_cap") == 60


def test_the_manifest_and_the_code_agree_on_every_default():
    """Two places declare the same six settings. Drift is silent: the form shows one default and
    the code uses another, and nobody sees it until someone wonders why the box does nothing."""
    from core import settings

    schema = yaml.safe_load(open(os.path.join(ROOT, "plugin.yaml")))["config_schema"]

    for key, spec in schema.items():
        if key in settings.BOOL_DEFAULTS:
            assert spec["default"] == settings.BOOL_DEFAULTS[key], key
        elif key in settings.TEXT_DEFAULTS:
            assert spec["default"] == settings.TEXT_DEFAULTS[key], key
        else:
            default, low, high = settings.INT_BOUNDS[key]
            assert spec["default"] == default, key
            # a bound the form does not know is a value the code silently rewrites
            assert spec.get("min") == low and spec.get("max") == high, key


def test_following_a_suggestion_is_off_unless_asked(monkeypatch):
    """A suggestion is advice. Acting on it unasked would be the plugin entering a state on its
    own, which is the one thing it must not do by default."""
    import importlib

    plugin = importlib.import_module("__init__")

    started = []
    monkeypatch.setattr(plugin.engine, "enter",
                        lambda key, minutes=None, **kw: started.append(key) or "entered")
    monkeypatch.setattr(plugin.engine, "peek", lambda: None)

    advice = "this looks like a walk · same tool failed 3x in a row · /walk"

    settings.bind(Host({}))
    assert plugin._follow(advice, "chat-1", "discord") is None
    assert started == []

    settings.bind(Host({"suggest_autofollow": True}))
    plugin._follow(advice, "chat-1", "discord")
    assert started == ["walk"], "on means it follows, and follows the state it named"

