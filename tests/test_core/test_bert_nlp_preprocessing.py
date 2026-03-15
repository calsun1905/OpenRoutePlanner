"""
BERT NLP preprocessing helper tests.

Bu testler model yüklemeden token normalizasyonu ve span çıkarım
davranışını doğrular.
"""

import os
import sys


backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

from bert_nlp_engine import (
    extract_candidate_spans,
    normalize_token_with_role,
    is_likely_action_token,
    is_poi_concept_term,
    extract_poi_concept,
    apply_intent_conflict_matrix,
    PlaceDatabase,
)


def test_plain_loc_suffix_does_not_trim_short_place_name():
    stem, role_hint = normalize_token_with_role("Galata")
    assert stem == "galata"
    assert role_hint is None


def test_plain_loc_suffix_trims_long_token():
    stem, role_hint = normalize_token_with_role("Uskudarda")
    assert role_hint == "loc"
    assert stem in {"üsküdar", "uskudar"}


def test_noise_word_gidelim_filtered_from_spans():
    spans = extract_candidate_spans("Kadıköy'e gidelim")
    normalized_values = {item["normalized"] for item in spans}
    assert "gidelim" not in normalized_values


def test_noise_word_dolas_filtered_from_multi_query():
    spans = extract_candidate_spans("Galata Karaköy Taksim dolaş")
    normalized_values = {item["normalized"] for item in spans}
    assert "dolaş" not in normalized_values
    assert "dolas" not in normalized_values


def test_action_token_ariyorum_detected():
    assert is_likely_action_token("arıyorum") is True
    assert is_likely_action_token("ariyorum") is True


def test_poi_concept_term_detects_cami():
    assert is_poi_concept_term("cami") is True


def test_extract_poi_concept_ignores_detected_location_span():
    concept = extract_poi_concept(
        "maltepe'de cami arıyorum",
        detected_places=[{"start": 0, "end": 10}],
    )
    assert concept == "cami"


def test_intent_conflict_matrix_promotes_poi_over_single_without_direction():
    final_type, final_conf, meta = apply_intent_conflict_matrix(
        "single",
        0.81,
        has_poi_cue=True,
        has_multi_cue=False,
        direction_hints=False,
        unique_place_count=1,
        low_margin=False,
    )
    assert final_type == "poi"
    assert final_conf >= 0.81
    assert meta["reason"] == "poi-cue-no-direction=>poi"


def test_intent_conflict_matrix_promotes_route_when_direction_present():
    final_type, final_conf, meta = apply_intent_conflict_matrix(
        "poi",
        0.60,
        has_poi_cue=True,
        has_multi_cue=False,
        direction_hints=True,
        unique_place_count=2,
        low_margin=True,
        route_intent_cue=True,
    )
    assert final_type == "route"
    assert final_conf >= 0.80
    assert meta["reason"] == "direction+multi-place=>route"


def test_prefetch_osm_candidates_respects_zero_budget(monkeypatch):
    db = PlaceDatabase(
        use_osm=True,
        prefer_osm_first=True,
        seed_dynamic_cache=False,
        seed_local_places=False,
        seed_static_places=False,
        seed_user_locations=False,
    )
    db._osm_prefetch_budget_sec = 0.0

    calls = {"count": 0}

    monkeypatch.setattr(db, "_build_osm_prefetch_queries", lambda query, max_queries=6: ["kadikoy", "besiktas"])

    def fake_cache(query, limit=5, deadline_ts=None):
        calls["count"] += 1
        return 1

    monkeypatch.setattr(db, "cache_osm_results", fake_cache)

    added = db.prefetch_osm_candidates("kadikoy besiktas")
    assert added == 0
    assert calls["count"] == 0
