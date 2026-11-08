"""The bundled artifacts are pinned by constants; the loader and selector are tested for their own checks.

EXPECTED, BRIDGE, and the provenance values pin the bundled Open Collider examples
here, and each content hash is recomputed independently. These tests prove the loader
itself validates required fields, top-level shape, kind, status, bridge/body
consistency, and content_hash, refusing each when it has drifted, and that the bank
loads as one set of six with unique ids.

Selection is tested against the same loaded bank: fresh is deterministic per seed and
excludes prior families, deepen and refresh restrict to the families of loved/liked
ids, counts bound the result, the caller's sets and the bank are never mutated, and
each refusal names the constraint it refused.

One opt-in check reads a local Open Collider checkout (ANTEMUSE_OC_REPO, else the
development path) and asserts each body appears verbatim in the prompt file its
provenance names; it skips when that checkout is absent. Otherwise no test resolves
repository, license, or the other provenance values upstream — those are asserted
here as recorded constants. No test makes a network or model call.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import collider  # noqa: E402

PLUGIN = Path(__file__).resolve().parents[1]
ARTIFACT = PLUGIN / "data" / "collider" / "acoustic_niche.json"

REPOSITORY = "CL-ML/open-collider-research"
PINNED_COMMIT = "6ed948a"
SOURCE_PATH = "OC_data/creativity_engine/T01_fresh_DS12_b1d535f4/prompt.md"
LICENSE = "CC-BY-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
ATTRIBUTION = (
    "Cédric Lion (2026), Open Collider: Methodology and Dataset for "
    "Bisociation-Based Idea Generation, CL-ML/open-collider-research @ 6ed948a"
)

BRIDGE = "What if ideas could partition conceptual frequency space to avoid interference?"

EXPECTED_MECHANISM = (
    "Species partition a shared acoustic space by vocalizing in non-overlapping "
    "frequency bands, giving every species its own channel; they share by dividing "
    "the spectrum instead of competing inside one band."
)

EXPECTED_BODY = (
    "1. **Acoustic niche hypothesis** — A soundscape ecologist studying frequency "
    "partitioning — whose work reveals that animals evolve to vocalize in "
    "non-overlapping frequency bands, creating a structured acoustic space where "
    "every species has its channel. They share by dividing. What if ideas could "
    "partition conceptual frequency space to avoid interference?"
)

EXPECTED = {
    "collider_acoustic_daylight_imaging": {
        "family": "bioacoustics",
        "title": "Acoustic daylight imaging",
        "mechanism": "The random ambient noise of the ocean carries enough information to image objects without any active pinging: the noise itself is the signal.",
        "bridge_question": "Could conceptual noise contain hidden information about idea space structure?",
        "body": "3. **Acoustic daylight imaging** — An ambient noise researcher studying passive sonar — whose work demonstrates that the random noise of the ocean contains enough information to image objects without active pinging. The noise is the signal. Could conceptual noise contain hidden information about idea space structure?",
        "content_hash": "sha256:9da18a5c4a4c3f25ec8096e4120ecd3596da11477e8ed4683ab498eeb62fcd95",
        "path": "OC_data/creativity_engine/T01_fresh_DS12_b1d535f4/prompt.md",
    },
    "collider_acoustic_niche_hypothesis": {
        "family": "bioacoustics",
        "title": "Acoustic niche hypothesis",
        "mechanism": EXPECTED_MECHANISM,
        "bridge_question": BRIDGE,
        "body": EXPECTED_BODY,
        "content_hash": "sha256:eb9fce51ff17314f703c44c7d0733070aa31c62ad0312a2b0b54f5e617c18136",
        "path": "OC_data/creativity_engine/T01_fresh_DS12_b1d535f4/prompt.md",
    },
    "collider_fairy_ring_formation": {
        "family": "mycology",
        "title": "Fairy ring formation",
        "mechanism": "Circular mushroom patterns emerge from nutrient-depletion waves that create self-reinforcing growth boundaries; the ring expands because the center becomes toxic to its own growth, forcing exploration outward.",
        "bridge_question": "How might creative systems poison their own successful patterns to force expansion?",
        "body": "4. **Fairy ring formation** — A mathematical mycologist studying fairy rings — whose work demonstrates that circular mushroom patterns emerge from nutrient depletion waves that create self-reinforcing growth boundaries. The ring expands because the center becomes toxic to its own growth, forcing exploration. How might creative systems poison their own successful patterns to force expansion?",
        "content_hash": "sha256:ebfa827bd68913306bd078ede34b3aa966d52e6ef65355435c8960aa75031ee7",
        "path": "OC_data/creativity_engine/T06_fresh_DS1_40c6b87a/prompt.md",
    },
    "collider_lombard_effect_dynamics": {
        "family": "bioacoustics",
        "title": "Lombard effect dynamics",
        "mechanism": "Animals involuntarily raise their pitch and volume in noise, but the adaptation also reduces the information content of the signal: shouting distorts the message it is meant to carry.",
        "bridge_question": "How might creative systems avoid conceptual shouting that reduces idea fidelity?",
        "body": "2. **Lombard effect dynamics** — A bioacoustics researcher studying noise adaptation — whose work shows that animals involuntarily raise their pitch and volume in noise, but this adaptation reduces information content. Shouting distorts the message. How might creative systems avoid conceptual shouting that reduces idea fidelity?",
        "content_hash": "sha256:6e478f148207ce3e6c29c9054de81f569f7a84e87f6660e3e35fb8648046a5f1",
        "path": "OC_data/creativity_engine/T01_fresh_DS12_b1d535f4/prompt.md",
    },
    "collider_mycelial_network_architecture": {
        "family": "mycology",
        "title": "Mycelial network architecture",
        "mechanism": "Underground fungal networks route resources toward where they will generate the highest future returns, a distributed investment system without central planning; chemical gradient persistence keeps profitable routes and abandons unprofitable ones.",
        "bridge_question": "How might idea generation systems develop memory of fertile collision zones without explicit tracking?",
        "body": "1. **Mycelial network architecture** — A mycorrhizal ecologist studying fungal networks — whose work reveals that underground fungal networks don't just connect plants, but actively route resources to where they'll generate the highest future returns, creating a distributed investment system without central planning. The network remembers profitable routes and abandons unprofitable ones through chemical gradient persistence. How might idea generation systems develop memory of fertile collision zones without explicit tracking?",
        "content_hash": "sha256:378ac966658130b4d645dbe24288d105ada8378ced434892852ccd40c813de53",
        "path": "OC_data/creativity_engine/T06_fresh_DS1_40c6b87a/prompt.md",
    },
    "collider_selective_autophagy": {
        "family": "cell_biology",
        "title": "Selective autophagy",
        "mechanism": "Cells tag damaged components with ubiquitin markers that attract autophagy machinery to engulf and digest them; the cell eats its broken parts to stay healthy.",
        "bridge_question": "How might idea systems selectively digest failed concepts to fuel new generation?",
        "body": "1. **Selective autophagy** — An autophagy researcher studying cellular recycling — whose work reveals that cells tag damaged components with ubiquitin markers that attract autophagy machinery to engulf and digest them. The cell eats its broken parts to stay healthy. How might idea systems selectively digest failed concepts to fuel new generation?",
        "content_hash": "sha256:f62754e80f3160d2329952023d3fd4e5eea9906025856540bbaddf1370f4e06c",
        "path": "OC_data/creativity_engine/T03_fresh_DS11_23d8845b/prompt.md",
    },
}

# Filename order is the bank's source order: load_bank sorts paths.
BANK_IDS = [
    "collider_acoustic_daylight_imaging",
    "collider_acoustic_niche_hypothesis",
    "collider_fairy_ring_formation",
    "collider_lombard_effect_dynamics",
    "collider_mycelial_network_architecture",
    "collider_selective_autophagy",
]

BIOACOUSTIC_IDS = [
    "collider_acoustic_daylight_imaging",
    "collider_acoustic_niche_hypothesis",
    "collider_lombard_effect_dynamics",
]
MYCOLOGY_IDS = [
    "collider_fairy_ring_formation",
    "collider_mycelial_network_architecture",
]


def _hash(mechanism: str, bridge_question: str) -> str:
    digest = hashlib.sha256(
        (mechanism + "\n" + bridge_question).encode("utf-8")
    ).hexdigest()
    return "sha256:" + digest


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def _write(tmp_path: Path, data) -> Path:
    path = Path(tmp_path) / "artifact.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _ids(artifacts) -> list:
    return [artifact["id"] for artifact in artifacts]


def _bank() -> list:
    return collider.load_bank()


def test_bundled_artifact_loads_with_required_values():
    data = collider.load_artifact(ARTIFACT)

    assert data["id"] == "collider_acoustic_niche_hypothesis"
    assert data["kind"] == "collider_example"
    assert data["family"] == "bioacoustics"
    assert data["title"] == "Acoustic niche hypothesis"
    assert data["mechanism"] == EXPECTED_MECHANISM
    assert data["verification_status"] == "generated_example"
    for field in collider.REQUIRED_FIELDS:
        assert data[field] not in (None, "", {}, []), field


def test_content_hash_matches_mechanism_and_bridge():
    data = _artifact()
    assert data["content_hash"] == _hash(data["mechanism"], data["bridge_question"])
    assert collider.load_artifact(ARTIFACT)["content_hash"] == data["content_hash"]


def test_body_equals_the_recorded_source_entry():
    body = _artifact()["body"]

    assert body == EXPECTED_BODY
    assert BRIDGE in body


def test_missing_required_field_raises(tmp_path):
    data = _artifact()
    del data["mechanism"]
    with pytest.raises(ValueError, match="mechanism"):
        collider.load_artifact(_write(tmp_path, data))


def test_tampered_mechanism_raises(tmp_path):
    data = _artifact()
    data["mechanism"] = data["mechanism"] + " And then something else."
    with pytest.raises(ValueError, match="content_hash"):
        collider.load_artifact(_write(tmp_path, data))


def test_tampered_bridge_question_raises(tmp_path):
    data = _artifact()
    data["bridge_question"] = "What if ideas could all share one channel?"
    with pytest.raises(ValueError, match="content_hash"):
        collider.load_artifact(_write(tmp_path, data))


def test_bridge_rewritten_with_recomputed_hash_raises(tmp_path):
    data = _artifact()
    data["bridge_question"] = "What if ideas could all share one channel?"
    data["content_hash"] = _hash(data["mechanism"], data["bridge_question"])
    with pytest.raises(ValueError, match="bridge_question must appear in body"):
        collider.load_artifact(_write(tmp_path, data))


def test_reformatted_body_whitespace_still_loads(tmp_path):
    data = _artifact()
    data["body"] = data["body"].replace(" every species", "\n\n   every species")
    loaded = collider.load_artifact(_write(tmp_path, data))

    assert BRIDGE in " ".join(loaded["body"].split())


def test_invalid_verification_status_raises(tmp_path):
    data = _artifact()
    data["verification_status"] = "verified_fact"
    with pytest.raises(ValueError, match="verification_status"):
        collider.load_artifact(_write(tmp_path, data))


def test_kind_must_be_collider_example(tmp_path):
    data = _artifact()
    data["kind"] = "walk_state"
    with pytest.raises(ValueError, match="kind"):
        collider.load_artifact(_write(tmp_path, data))


@pytest.mark.parametrize(
    "bad_hash",
    [
        "",
        "a" * 64,  # no algorithm prefix
        "sha256:" + "A" * 64,  # uppercase hex
        "sha256:" + "a" * 63,  # too short
        "sha256:" + "a" * 64 + "b",  # too long
        "md5:" + "a" * 64,  # wrong algorithm
    ],
)
def test_malformed_content_hash_format_raises(tmp_path, bad_hash):
    data = _artifact()
    data["content_hash"] = bad_hash
    with pytest.raises(ValueError, match="content_hash must be 'sha256:'"):
        collider.load_artifact(_write(tmp_path, data))


def test_content_hash_with_trailing_newline_raises(tmp_path):
    data = _artifact()
    data["content_hash"] = _hash(data["mechanism"], data["bridge_question"]) + "\n"
    with pytest.raises(ValueError, match="content_hash must be 'sha256:'"):
        collider.load_artifact(_write(tmp_path, data))


def test_top_level_json_list_raises(tmp_path):
    with pytest.raises(ValueError, match="JSON object"):
        collider.load_artifact(_write(tmp_path, [{"id": "not-an-object"}]))


def test_provenance_is_exact_and_license_is_cc_by():
    provenance = collider.load_artifact(ARTIFACT)["provenance"]

    assert provenance["repository"] == REPOSITORY
    assert provenance["pinned_commit"] == PINNED_COMMIT
    assert provenance["path"] == SOURCE_PATH
    assert provenance["license"] == LICENSE
    assert provenance["license_url"] == LICENSE_URL
    assert provenance["attribution"] == ATTRIBUTION


def test_license_other_than_cc_by_raises(tmp_path):
    data = _artifact()
    data["provenance"]["license"] = "unverified_research_artifact"
    with pytest.raises(ValueError, match="CC-BY-4.0"):
        collider.load_artifact(_write(tmp_path, data))


def test_missing_license_url_raises(tmp_path):
    data = _artifact()
    del data["provenance"]["license_url"]
    with pytest.raises(ValueError, match="license_url"):
        collider.load_artifact(_write(tmp_path, data))


def test_missing_attribution_raises(tmp_path):
    """CC BY 4.0 requires credit; a copy without it must not load."""
    data = _artifact()
    del data["provenance"]["attribution"]
    with pytest.raises(ValueError, match="attribution"):
        collider.load_artifact(_write(tmp_path, data))


def test_altered_attribution_raises(tmp_path):
    data = _artifact()
    data["provenance"]["attribution"] = "someone else"
    with pytest.raises(ValueError, match="attribution"):
        collider.load_artifact(_write(tmp_path, data))


def test_module_constants_match_the_bank():
    """The loader's pinned licence values are the ones the bank actually carries."""
    assert collider.ARTIFACT_LICENSE == LICENSE
    assert collider.ARTIFACT_LICENSE_URL == LICENSE_URL
    assert collider.ARTIFACT_ATTRIBUTION == ATTRIBUTION


# ------------------------------------------------------- licensing evidence (C3)

LICENSING = PLUGIN / "data" / "collider" / "licensing"
LICENSE_RECORD = json.loads((LICENSING / "upstream-license.json").read_text(encoding="utf-8"))


def _git_blob_sha(path: Path) -> str:
    """Git's object id for a file, so a recorded upstream blob can be re-derived."""
    raw = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()


def test_upstream_licence_text_matches_the_recorded_blob_shas():
    """The stored upstream texts are the blobs we cite, checked offline by digest."""
    for entry in LICENSE_RECORD["upstream"]["files"]:
        stored = LICENSING / entry["path"]
        assert stored.exists(), entry["path"]
        assert _git_blob_sha(stored) == entry["blob_sha"], entry["path"]
        assert stored.stat().st_size == entry["size_bytes"], entry["path"]


def test_quoted_upstream_clauses_appear_verbatim_in_the_stored_text():
    """Every quoted clause is a substring of the text whose digest we just checked."""
    for entry in LICENSE_RECORD["upstream"]["files"]:
        text = " ".join((LICENSING / entry["path"]).read_text(encoding="utf-8").split())
        quote = " ".join(entry["quoted_clause"].split())
        for fragment in quote.split("... "):
            assert " ".join(fragment.split()) in text, (entry["path"], fragment[:60])


def test_record_pins_the_commit_the_artifacts_name():
    commit = LICENSE_RECORD["upstream"]["commit"]
    assert commit == "6ed948ac9e5b5dcc39b82959bbfe1a644e0f7d7f"
    for artifact in _bank():
        assert commit.startswith(artifact["provenance"]["pinned_commit"])


def test_attribution_notice_accompanies_the_bank():
    """CC BY 4.0 needs credit and a licence link that travel with the copies."""
    notice = " ".join(
        (PLUGIN / "data" / "collider" / "ATTRIBUTION.md")
        .read_text(encoding="utf-8")
        .split()
    )
    assert ATTRIBUTION in notice
    assert collider.ARTIFACT_LICENSE_URL in notice
    assert collider.ARTIFACT_LICENSE in notice
    assert "not affiliated" in notice
    for path in sorted((PLUGIN / "data" / "collider").glob("*.json")):
        assert path.name in notice, path.name


def test_provenance_missing_field_raises(tmp_path):
    data = _artifact()
    del data["provenance"]["pinned_commit"]
    with pytest.raises(ValueError, match="pinned_commit"):
        collider.load_artifact(_write(tmp_path, data))


# ---------------------------------------------------------------- the whole bank


def test_bank_loads_six_artifacts_in_source_order():
    bank = _bank()

    assert _ids(bank) == BANK_IDS
    assert len(set(BANK_IDS)) == 6
    for artifact in bank:
        assert set(artifact) == set(collider.REQUIRED_FIELDS), artifact["id"]
        assert artifact["kind"] == "collider_example"
        assert artifact["verification_status"] == "generated_example"


def test_bank_families_and_titles_are_pinned():
    families = {artifact["id"]: artifact["family"] for artifact in _bank()}

    assert families == {artifact_id: spec["family"] for artifact_id, spec in EXPECTED.items()}
    for artifact in _bank():
        assert artifact["title"] == EXPECTED[artifact["id"]]["title"]
        assert artifact["bridge_question"] == EXPECTED[artifact["id"]]["bridge_question"]


def test_bank_bodies_are_the_pinned_source_entries():
    for artifact in _bank():
        spec = EXPECTED[artifact["id"]]
        assert artifact["body"] == spec["body"]
        assert artifact["mechanism"] == spec["mechanism"]
        # The bridge question is the source entry's own closing question.
        assert spec["body"].endswith(spec["bridge_question"])


def test_bank_content_hashes_validate_independently():
    for artifact in _bank():
        expected = _hash(artifact["mechanism"], artifact["bridge_question"])
        assert artifact["content_hash"] == expected, artifact["id"]
        assert artifact["content_hash"] == EXPECTED[artifact["id"]]["content_hash"]


def test_bank_provenance_is_pinned_per_artifact():
    for artifact in _bank():
        provenance = artifact["provenance"]
        assert provenance["repository"] == REPOSITORY
        assert provenance["pinned_commit"] == PINNED_COMMIT
        assert provenance["license"] == LICENSE
        assert provenance["license_url"] == LICENSE_URL
        assert provenance["attribution"] == ATTRIBUTION
        assert provenance["path"] == EXPECTED[artifact["id"]]["path"]
        assert provenance["path"].startswith("OC_data/creativity_engine/T")
        assert provenance["path"].endswith("/prompt.md")


def test_bank_paths_point_at_the_source_that_carries_each_body():
    repo = Path(
        os.environ.get(
            "ANTEMUSE_OC_REPO",
            "/home/ryan/.hermes/cache/scratch/concept-re/open-collider-research",
        )
    )
    if not (repo / "OC_data" / "creativity_engine").is_dir():
        pytest.skip("no local Open Collider checkout to cross-check bodies against")

    for artifact in _bank():
        prompt = repo / artifact["provenance"]["path"]
        assert prompt.is_file(), artifact["id"]
        lines = prompt.read_text(encoding="utf-8").splitlines()
        assert artifact["body"] in lines, artifact["id"]
        assert lines.count(artifact["body"]) == 1, artifact["id"]


def test_bank_rejects_duplicate_ids(tmp_path):
    data = _artifact()
    for name in ("a.json", "b.json"):
        (tmp_path / name).write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate artifact id"):
        collider.load_bank(tmp_path)


def test_bank_refuses_an_empty_or_missing_directory(tmp_path):
    with pytest.raises(ValueError, match="no collider artifacts"):
        collider.load_bank(tmp_path)
    with pytest.raises(ValueError, match="no collider artifacts"):
        collider.load_bank(tmp_path / "absent")


# -------------------------------------------------------------------- selection


def test_fresh_is_deterministic_per_seed():
    first = collider.select_sources(_bank(), strategy="fresh", seed=7, count=3)
    second = collider.select_sources(_bank(), strategy="fresh", seed=7, count=3)

    assert _ids(first) == _ids(second)


def test_fresh_excludes_previous_families():
    selected = collider.select_sources(
        _bank(), strategy="fresh", seed=11, previous_families={"bioacoustics"}
    )

    assert _ids(selected) == ["collider_fairy_ring_formation", "collider_mycelial_network_architecture", "collider_selective_autophagy"]
    assert all(artifact["family"] != "bioacoustics" for artifact in selected)


def test_fresh_seed_actually_changes_the_draw():
    draws = {
        tuple(_ids(collider.select_sources(_bank(), strategy="fresh", seed=seed, count=2)))
        for seed in range(5)
    }

    assert len(draws) > 1


def test_fresh_returns_source_order_after_seeded_selection():
    bank = _bank()
    position = {artifact_id: index for index, artifact_id in enumerate(BANK_IDS)}

    for seed in range(6):
        selected = collider.select_sources(bank, strategy="fresh", seed=seed, count=4)
        chosen = [position[artifact_id] for artifact_id in _ids(selected)]
        assert chosen == sorted(chosen)
        assert len(chosen) == 4


def test_fresh_with_every_family_excluded_names_the_constraint():
    every_family = {artifact["family"] for artifact in _bank()}

    with pytest.raises(ValueError, match="previous_families"):
        collider.select_sources(
            _bank(), strategy="fresh", seed=1, previous_families=every_family
        )


def test_fresh_ignores_unknown_previous_families():
    selected = collider.select_sources(
        _bank(), strategy="fresh", seed=3, previous_families={"paleontology"}
    )

    assert _ids(selected) == BANK_IDS


def test_deepen_restricts_to_families_of_loved_ids():
    selected = collider.select_sources(
        _bank(), strategy="deepen", seed=5, loved={"collider_mycelial_network_architecture"}
    )

    assert _ids(selected) == MYCOLOGY_IDS
    assert {artifact["family"] for artifact in selected} == {"mycology"}


def test_deepen_accepts_a_single_loved_id_from_each_family():
    selected = collider.select_sources(
        _bank(),
        strategy="deepen",
        seed=5,
        loved={"collider_selective_autophagy", "collider_lombard_effect_dynamics"},
    )

    # One loved id pulls its whole family in: lombard brings both other bioacoustics.
    assert _ids(selected) == [
        "collider_acoustic_daylight_imaging",
        "collider_acoustic_niche_hypothesis",
        "collider_lombard_effect_dynamics",
        "collider_selective_autophagy",
    ]


def test_deepen_with_no_loved_ids_names_loved():
    with pytest.raises(ValueError, match="loved is empty"):
        collider.select_sources(_bank(), strategy="deepen", seed=1)
    with pytest.raises(ValueError, match="loved is empty"):
        collider.select_sources(_bank(), strategy="deepen", seed=1, loved=set())


def test_deepen_with_unknown_loved_ids_names_the_ids():
    with pytest.raises(ValueError, match="none of the ids in loved"):
        collider.select_sources(
            _bank(), strategy="deepen", seed=1, loved={"collider_not_in_the_bank"}
        )


def test_refresh_restricts_to_families_of_loved_and_liked_ids():
    selected = collider.select_sources(
        _bank(),
        strategy="refresh",
        seed=2,
        loved={"collider_selective_autophagy"},
        liked={"collider_fairy_ring_formation"},
    )

    assert _ids(selected) == [
        "collider_fairy_ring_formation",
        "collider_mycelial_network_architecture",
        "collider_selective_autophagy",
    ]


def test_refresh_uses_liked_alone_and_loved_alone():
    liked_only = collider.select_sources(
        _bank(), strategy="refresh", seed=2, liked={"collider_mycelial_network_architecture"}
    )
    loved_only = collider.select_sources(
        _bank(), strategy="refresh", seed=2, loved={"collider_mycelial_network_architecture"}
    )

    assert _ids(liked_only) == MYCOLOGY_IDS
    assert _ids(loved_only) == MYCOLOGY_IDS


def test_refresh_without_signals_names_the_constraint():
    with pytest.raises(ValueError, match="loved or liked is empty"):
        collider.select_sources(_bank(), strategy="refresh", seed=1)
    with pytest.raises(ValueError, match="loved or liked is empty"):
        collider.select_sources(_bank(), strategy="refresh", seed=1, loved=set(), liked=set())


def test_refresh_with_unknown_signals_names_the_ids():
    with pytest.raises(ValueError, match="none of the ids in loved or liked"):
        collider.select_sources(
            _bank(), strategy="refresh", seed=1, liked={"collider_absent"}
        )


def test_selection_never_mutates_the_caller_arguments():
    bank = _bank()
    snapshot = json.dumps(bank, sort_keys=True)
    previous = {"bioacoustics"}
    loved = {"collider_selective_autophagy"}
    liked = {"collider_mycelial_network_architecture"}

    collider.select_sources(
        bank,
        strategy="refresh",
        seed=4,
        previous_families=previous,
        loved=loved,
        liked=liked,
        count=2,
    )
    collider.select_sources(
        bank, strategy="fresh", seed=4, previous_families=previous, count=2
    )

    assert json.dumps(bank, sort_keys=True) == snapshot
    assert previous == {"bioacoustics"}
    assert loved == {"collider_selective_autophagy"}
    assert liked == {"collider_mycelial_network_architecture"}


def test_selection_accepts_frozensets_without_copying_them_away():
    previous = frozenset({"mycology"})
    selected = collider.select_sources(
        _bank(), strategy="fresh", seed=1, previous_families=previous
    )

    assert previous == frozenset({"mycology"})
    assert {artifact["family"] for artifact in selected} == {"bioacoustics", "cell_biology"}


def test_selection_returns_the_loaded_records_with_provenance():
    bank = _bank()
    by_id = {artifact["id"]: artifact for artifact in bank}
    selected = collider.select_sources(bank, strategy="fresh", seed=9, count=2)

    for artifact in selected:
        assert artifact is by_id[artifact["id"]]
        assert artifact["provenance"]["repository"] == REPOSITORY


@pytest.mark.parametrize("count", [0, 1, 2])
def test_count_bounds_the_selection(count):
    selected = collider.select_sources(_bank(), strategy="fresh", seed=3, count=count)

    assert len(selected) == count


def test_count_beyond_the_candidates_returns_all_of_them():
    selected = collider.select_sources(_bank(), strategy="fresh", seed=3, count=99)

    assert _ids(selected) == BANK_IDS


def test_count_zero_selects_nothing_but_still_validates_the_strategy():
    assert collider.select_sources(_bank(), strategy="fresh", seed=3, count=0) == []
    assert collider.select_sources(_bank(), strategy="deepen", seed=3, loved={"collider_selective_autophagy"}, count=0) == []


@pytest.mark.parametrize("bad_count", [-1, 1.5, "2", True])
def test_invalid_count_raises(bad_count):
    with pytest.raises(ValueError, match="count must be a non-negative integer"):
        collider.select_sources(_bank(), strategy="fresh", seed=1, count=bad_count)


def test_unknown_strategy_raises():
    with pytest.raises(ValueError, match="strategy must be one of"):
        collider.select_sources(_bank(), strategy="explore", seed=1)


def test_empty_artifacts_raise():
    with pytest.raises(ValueError, match="non-empty"):
        collider.select_sources([], strategy="fresh", seed=1)


def test_selection_rejects_records_without_id_or_family():
    with pytest.raises(ValueError, match="non-empty string id"):
        collider.select_sources([{"family": "mycology"}], strategy="fresh", seed=1)
    with pytest.raises(ValueError, match="non-empty family"):
        collider.select_sources([{"id": "collider_x"}], strategy="fresh", seed=1)
    with pytest.raises(ValueError, match="duplicate artifact id"):
        collider.select_sources(
            [{"id": "collider_x", "family": "mycology"}] * 2, strategy="fresh", seed=1
        )


def test_non_string_signal_sets_raise():
    with pytest.raises(ValueError, match="previous_families must contain only strings"):
        collider.select_sources(
            _bank(),
            strategy="fresh",
            seed=1,
            previous_families={"mycology", 3},  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="loved must be a set of strings"):
        collider.select_sources(_bank(), strategy="deepen", seed=1, loved="collider_x")
