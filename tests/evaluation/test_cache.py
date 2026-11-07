"""The cache must never let one experiment condition answer for another."""
from __future__ import annotations

import json
import os
import re
import sys

import pytest

from . import load  # noqa: E402

cache = load("cache")
JsonlCache = cache.JsonlCache
condition_cache_key = cache.condition_cache_key

BASE = dict(
    model="deepseek-v4.1",
    condition="baseline",
    task_id="task-17",
    prompt_version="p3",
    source_version="s9",
    seed=1234,
)

STRING_FIELDS = ("model", "condition", "task_id", "prompt_version", "source_version")


def _key(**overrides):
    fields = dict(BASE)
    fields.update(overrides)
    return condition_cache_key(**fields)


def _reject_constant(token):
    raise AssertionError(f"shard contains non-JSON constant {token!r}")


def _strict_loads(line):
    """Parse one shard line the way a strict consumer (jq, Go, Rust) would."""
    return json.loads(line, parse_constant=_reject_constant)


def test_identical_inputs_produce_identical_keys_across_calls():
    assert _key() == _key()
    assert isinstance(_key(), str)


def test_changing_each_condition_field_changes_the_key():
    base = _key()
    for field, value in [
        ("model", "deepseek-v4.1-mini"),
        ("condition", "treatment"),
        ("task_id", "task-18"),
        ("prompt_version", "p4"),
        ("source_version", "s10"),
        ("seed", 1235),
    ]:
        assert _key(**{field: value}) != base, field


def test_keys_are_64_lowercase_hex_and_do_not_leak_source_text():
    key = _key(condition="a very private condition string")
    assert re.fullmatch(r"[0-9a-f]{64}", key)
    assert "private" not in key.lower()
    assert "deepseek" not in key.lower()
    assert "task-17" not in key.lower()


# The expected digest below is derived independently of the implementation, from
# BASE written out as canonical JSON (sorted keys, no whitespace, UTF-8):
#
#   {"condition":"baseline","model":"deepseek-v4.1","prompt_version":"p3",
#    "seed":1234,"source_version":"s9","task_id":"task-17"}
#
#   printf '%s' '<that exact 124-byte string>' | sha256sum
#   -> 4c2fe370f2cc9277ec40aa06ba46748e2e9a3c52b24e70ba8304e267ceeba3dc
#
# Pinning it is what makes canonical JSON a testable requirement rather than an
# assumption: an implementation that skips sort_keys/separators (or hashes a
# different field set) produces a different digest. It also locks the on-disk
# key format, so a silent drift cannot orphan every shard without an error.
BASE_CANONICAL_JSON = (
    '{"condition":"baseline","model":"deepseek-v4.1","prompt_version":"p3",'
    '"seed":1234,"source_version":"s9","task_id":"task-17"}'
)
BASE_EXPECTED_KEY = "4c2fe370f2cc9277ec40aa06ba46748e2e9a3c52b24e70ba8304e267ceeba3dc"


def test_base_key_matches_independently_derived_canonical_json_digest():
    # Re-derive the digest here from the literal canonical JSON, using only the
    # standard library, so the constant above is checked rather than trusted.
    import hashlib

    recomputed = hashlib.sha256(BASE_CANONICAL_JSON.encode("utf-8")).hexdigest()
    assert recomputed == BASE_EXPECTED_KEY
    # ...and the implementation agrees with that independent derivation.
    assert _key() == BASE_EXPECTED_KEY


@pytest.mark.parametrize("field", STRING_FIELDS)
@pytest.mark.parametrize("blank", ["", " ", "\t", "\n", "  \t\n "])
def test_empty_or_whitespace_only_identifiers_are_rejected(field, blank):
    # An unset condition must fail loudly instead of collapsing onto a shared
    # key with every other experiment that also left it blank.
    with pytest.raises(ValueError):
        _key(**{field: blank})


def test_padded_but_non_blank_identifiers_are_still_accepted():
    assert re.fullmatch(r"[0-9a-f]{64}", _key(model=" deepseek-v4.1 "))
    assert _key(model=" deepseek-v4.1 ") != _key(model="deepseek-v4.1")


def test_round_trip_returns_the_exact_record(tmp_path):
    cache = JsonlCache(tmp_path / "shard-0.jsonl")
    record = {"publish": False, "tokens": 42, "nested": {"tags": ["a", "b"]},
              "text": "the exact response body"}
    key = _key()

    assert cache.get(key) is None
    cache.put(key, record)

    assert cache.get(key) == record


def test_a_response_under_one_condition_is_invisible_under_another(tmp_path):
    cache = JsonlCache(tmp_path / "shard-0.jsonl")
    record = {"response": "belongs to baseline only"}
    cache.put(_key(condition="baseline"), record)

    assert cache.get(_key(condition="baseline")) == record
    assert cache.get(_key(condition="treatment")) is None
    assert cache.get(_key(model="another-model")) is None


def test_missing_keys_return_none(tmp_path):
    cache = JsonlCache(tmp_path / "shard-0.jsonl")
    assert cache.get(_key()) is None
    cache.put(_key(seed=7), {"ok": True})
    assert cache.get(_key(seed=8)) is None


def test_put_appends_one_json_object_with_key_and_record(tmp_path):
    path = tmp_path / "shard-0.jsonl"
    cache = JsonlCache(path)
    cache.put(_key(), {"a": 1})
    cache.put(_key(seed=2), {"a": 2})

    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2
    assert lines[0]["key"] == _key()
    assert lines[0]["record"] == {"a": 1}
    assert lines[1]["key"] == _key(seed=2)


def test_put_appends_after_a_preexisting_foreign_line_without_rewriting_it(tmp_path):
    """Shards are append-only: a line written by someone else must survive, first.

    A read-modify-write implementation that rebuilds the file would satisfy the
    line-count test above, so pre-seed the shard before the cache object exists
    and inspect the raw bytes. The foreign line must still be the first line,
    byte-for-byte, and the file must still end with exactly one newline.
    """
    path = tmp_path / "shard-0.jsonl"
    foreign = {"key": "foreign-key-from-another-writer", "record": {"owner": "other"}}
    foreign_line = json.dumps(foreign, sort_keys=True, separators=(",", ":"))
    path.write_text(foreign_line + "\n", encoding="utf-8")

    cache = JsonlCache(path)
    cache.put(_key(), {"a": 1})

    raw = path.read_bytes()
    assert raw.endswith(b"\n")
    assert raw.startswith(foreign_line.encode("utf-8") + b"\n")

    lines = [line for line in raw.decode("utf-8").splitlines() if line.strip()]
    assert len(lines) == 2
    assert json.loads(lines[0]) == foreign
    assert json.loads(lines[1]) == {"key": _key(), "record": {"a": 1}}
    # The pre-existing record is still retrievable, untouched, by its own key.
    assert cache.get("foreign-key-from-another-writer") == {"owner": "other"}


def test_every_written_line_is_strict_json(tmp_path):
    path = tmp_path / "shard-0.jsonl"
    cache = JsonlCache(path)
    cache.put(_key(), {"loss": 0.5, "nested": {"scores": [1, 2, 3]}, "ok": True})
    cache.put(_key(seed=2), {"loss": -0.25})

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    for line in lines:
        # _strict_loads rejects NaN/Infinity the way jq and non-Python parsers do.
        _strict_loads(line)


def test_put_rejects_nan_and_infinity_before_appending_anything(tmp_path):
    path = tmp_path / "shard-0.jsonl"
    cache = JsonlCache(path)

    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError):
            cache.put(_key(), {"loss": bad})

    # Serialization failed before the shard was opened: no file, no partial line.
    assert not path.exists()


def test_rejected_write_leaves_an_existing_shard_byte_identical(tmp_path):
    path = tmp_path / "shard-0.jsonl"
    cache = JsonlCache(path)
    cache.put(_key(), {"loss": 0.5})
    before = path.read_bytes()

    with pytest.raises(ValueError):
        cache.put(_key(seed=2), {"loss": float("nan")})

    after = path.read_bytes()
    assert after == before
    assert b"NaN" not in after
    # The good record is still readable; the rejected one never landed.
    assert cache.get(_key()) == {"loss": 0.5}
    assert cache.get(_key(seed=2)) is None


def test_truncated_second_entry_for_the_same_key_raises_not_stale_data(tmp_path):
    path = tmp_path / "shard-0.jsonl"
    good = json.dumps({"key": "k", "record": {"v": 1}}, sort_keys=True, separators=(",", ":"))
    truncated = '{"key":"k","record":{"v":2}'
    path.write_text(good + "\n" + truncated + "\n", encoding="utf-8")

    cache = JsonlCache(path)
    with pytest.raises(ValueError) as excinfo:
        cache.get("k")

    message = str(excinfo.value)
    assert str(path) in message
    assert ":2" in message


def test_get_raises_when_a_line_is_not_a_json_object(tmp_path):
    path = tmp_path / "shard-0.jsonl"
    path.write_text("[1, 2, 3]\n", encoding="utf-8")

    with pytest.raises(ValueError) as excinfo:
        JsonlCache(path).get("k")

    assert str(path) in str(excinfo.value)
    assert ":1" in str(excinfo.value)


def test_get_raises_when_the_record_is_not_a_json_object(tmp_path):
    path = tmp_path / "shard-0.jsonl"
    path.write_text('{"key":"k","record":"not an object"}\n', encoding="utf-8")

    with pytest.raises(ValueError) as excinfo:
        JsonlCache(path).get("k")

    assert str(path) in str(excinfo.value)
    assert ":1" in str(excinfo.value)


def test_bool_seed_is_rejected_so_true_cannot_collide_with_one():
    # JSON `true` and `1` are distinct values; a bool seed would serialize as
    # `true` here or silently alias the int 1 depending on the encoder. Reject
    # bools outright instead of guessing which the caller meant.
    with pytest.raises(TypeError):
        _key(seed=True)
    with pytest.raises(TypeError):
        _key(seed=False)
    # A plain int seed is the accepted form.
    assert re.fullmatch(r"[0-9a-f]{64}", _key(seed=1))


def test_put_refuses_to_append_to_a_shard_without_a_trailing_newline(tmp_path):
    """A crash-truncated tail must not be fused to a fresh record.

    A killed write leaves bytes with no final newline. Appending blindly would
    put two JSON objects on one line and make every key in that shard raise on
    read, so put must refuse before writing a single byte.
    """
    path = tmp_path / "shard-0.jsonl"
    truncated_tail = json.dumps(
        {"key": "old", "record": {"v": 0}}, sort_keys=True, separators=(",", ":")
    )
    path.write_text(truncated_tail, encoding="utf-8")
    before = path.read_bytes()
    cache = JsonlCache(path)

    with pytest.raises(ValueError) as excinfo:
        cache.put(_key(), {"v": 1})

    assert str(path) in str(excinfo.value)
    assert path.read_bytes() == before
    # The shard is untouched, not just re-readable: no new line, no new bytes.
    assert path.read_bytes().count(b"\n") == 0
    assert cache.get(_key()) is None
    assert cache.get("old") == {"v": 0}


def test_re_putting_the_same_key_appends_a_line_and_the_last_record_wins(tmp_path):
    """Append-only retries: both lines stay, the newest record answers get."""
    path = tmp_path / "shard-0.jsonl"
    cache = JsonlCache(path)
    key = _key()

    cache.put(key, {"attempt": 1, "text": "first"})
    cache.put(key, {"attempt": 2, "text": "second"})

    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2
    assert [json.loads(line)["record"] for line in lines] == [
        {"attempt": 1, "text": "first"},
        {"attempt": 2, "text": "second"},
    ]
    assert cache.get(key) == {"attempt": 2, "text": "second"}


def test_put_rejects_an_integer_dict_key_before_writing_anything(tmp_path):
    """JSON would rewrite {1: "a"} as {"1": "a"}, silently changing the record."""
    path = tmp_path / "shard-0.jsonl"
    cache = JsonlCache(path)
    cache.put(_key(), {"ok": True})
    before = path.read_bytes()

    with pytest.raises(TypeError) as excinfo:
        cache.put(_key(seed=2), {1: "a", 2: "b"})  # type: ignore[arg-type]

    message = str(excinfo.value)
    assert "record" in message
    assert "1" in message
    assert path.read_bytes() == before
    assert cache.get(_key(seed=2)) is None


def test_put_rejects_a_tuple_before_writing_anything(tmp_path):
    """JSON would rewrite ("a", "b") as ["a", "b"], breaking the exact record."""
    path = tmp_path / "shard-0.jsonl"
    cache = JsonlCache(path)
    cache.put(_key(), {"ok": True})
    before = path.read_bytes()

    with pytest.raises(TypeError) as excinfo:
        cache.put(_key(seed=2), {"tags": ("a", "b")})

    message = str(excinfo.value)
    assert "record['tags']" in message
    assert "tuple" in message
    assert path.read_bytes() == before
    assert cache.get(_key(seed=2)) is None


@pytest.mark.parametrize(
    "line",
    [
        '{"record":{"v":1}}\n',          # key field absent
        '{"key":123,"record":{"v":1}}\n',  # key present but not a string
        '{"key":null,"record":{"v":1}}\n',
    ],
)
def test_get_raises_when_an_entry_has_no_string_key(tmp_path, line):
    """Fail closed: a keyless line must not read as an ordinary miss."""
    path = tmp_path / "shard-0.jsonl"
    path.write_text(line, encoding="utf-8")

    with pytest.raises(ValueError) as excinfo:
        JsonlCache(path).get("123")

    message = str(excinfo.value)
    assert str(path) in message
    assert ":1" in message
    assert "key" in message
