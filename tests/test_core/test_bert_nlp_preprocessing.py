"""
BERT NLP preprocessing helper tests.

Bu testler model yüklemeden token normalizasyonu ve span çıkarım
davranışını doğrular.
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np


backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

import bert_nlp_engine as bert_module
from bert_nlp_engine import (
    extract_candidate_spans,
    get_bert_nlp_engine,
    normalize_place_key,
    normalize_token_with_role,
    is_likely_action_token,
    is_poi_concept_term,
    extract_poi_concept,
    apply_intent_conflict_matrix,
    should_rescue_poi_intent,
    has_explicit_route_pattern,
    has_confident_route_pair,
    _extract_plain_multi_places,
    PlaceDatabase,
)
from local_places import get_all_local_place_names, lookup as lookup_local_place


GOLD_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "bert_gold_tr_v1.jsonl"
ISTANBUL_DISTRICTS = [
    "Adalar", "Arnavutköy", "Ataşehir", "Avcılar", "Bağcılar", "Bahçelievler",
    "Bakırköy", "Başakşehir", "Bayrampaşa", "Beşiktaş", "Beykoz", "Beylikdüzü",
    "Beyoğlu", "Büyükçekmece", "Çatalca", "Çekmeköy", "Esenler", "Esenyurt",
    "Eyüpsultan", "Fatih", "Gaziosmanpaşa", "Güngören", "Kadıköy", "Kağıthane",
    "Kartal", "Küçükçekmece", "Maltepe", "Pendik", "Sancaktepe", "Sarıyer",
    "Silivri", "Sultanbeyli", "Sultangazi", "Şile", "Şişli", "Tuzla",
    "Ümraniye", "Üsküdar", "Zeytinburnu",
]
ISTANBUL_DISTRICT_ASCII_ALIASES = {
    "Arnavutköy": "arnavutkoy",
    "Ataşehir": "atasehir",
    "Avcılar": "avcilar",
    "Bağcılar": "bagcilar",
    "Bahçelievler": "bahcelievler",
    "Bakırköy": "bakirkoy",
    "Başakşehir": "basaksehir",
    "Bayrampaşa": "bayrampasa",
    "Beşiktaş": "besiktas",
    "Beylikdüzü": "beylikduzu",
    "Beyoğlu": "beyoglu",
    "Büyükçekmece": "buyukcekmece",
    "Çatalca": "catalca",
    "Çekmeköy": "cekmekoy",
    "Eyüpsultan": "eyupsultan",
    "Gaziosmanpaşa": "gaziosmanpasa",
    "Güngören": "gungoren",
    "Kadıköy": "kadikoy",
    "Kağıthane": "kagithane",
    "Küçükçekmece": "kucukcekmece",
    "Sarıyer": "sariyer",
    "Şile": "sile",
    "Şişli": "sisli",
    "Ümraniye": "umraniye",
    "Üsküdar": "uskudar",
}
REQUIRED_GOLD_TAGS = {
    "route-natural",
    "route-transit",
    "route-ambiguous",
    "poi-loc",
    "poi-contextual",
    "single-target",
    "multi-list",
    "unknown-chitchat",
    "typo",
    "scope",
    "false-positive",
    "mixed-intent",
}


def _load_gold_examples():
    with GOLD_DATA_PATH.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _place_matches_expected(actual, expected):
    actual_key = normalize_place_key(str(actual or ""))
    expected_key = normalize_place_key(str(expected or ""))
    return bool(
        actual_key
        and expected_key
        and (actual_key == expected_key or actual_key.endswith(" " + expected_key))
    )


def test_plain_loc_suffix_does_not_trim_short_place_name():
    stem, role_hint = normalize_token_with_role("Galata")
    assert stem == "galata"
    assert role_hint is None


def test_plain_loc_suffix_trims_long_token():
    stem, role_hint = normalize_token_with_role("Uskudarda")
    assert role_hint == "loc"
    assert stem in {"üsküdar", "uskudar"}


def test_plain_to_suffix_uses_known_place_roots():
    stem, role_hint = normalize_token_with_role("Taksime")
    assert stem == "taksim"
    assert role_hint == "to"


def test_object_suffix_keeps_place_name_without_route_role():
    stem, role_hint = normalize_token_with_role("Besiktas'i")
    assert stem == "beşiktaş"
    assert role_hint is None


def test_poi_concept_token_is_not_treated_as_direction():
    stem, role_hint = normalize_token_with_role("eczane")
    assert stem == "eczane"
    assert role_hint is None


def test_noise_word_gidelim_filtered_from_spans():
    spans = extract_candidate_spans("Kadıköy'e gidelim")
    normalized_values = {item["normalized"] for item in spans}
    assert "gidelim" not in normalized_values


def test_extract_candidate_spans_preserves_plain_route_roles():
    spans = extract_candidate_spans("kadikoyden maltepeye")
    role_map = {item["normalized"]: item["role_hint"] for item in spans}
    assert role_map["kadıköy"] == "from"
    assert role_map["maltepe"] == "to"


def test_extract_candidate_spans_preserves_apostrophe_route_roles():
    spans = extract_candidate_spans("kadıköy'den maltepe'ye")
    role_map = {item["normalized"]: item["role_hint"] for item in spans}
    assert role_map["kadıköy"] == "from"
    assert role_map["maltepe"] == "to"


def test_noise_word_dolas_filtered_from_multi_query():
    spans = extract_candidate_spans("Galata Karaköy Taksim dolaş")
    normalized_values = {item["normalized"] for item in spans}
    assert "dolaş" not in normalized_values
    assert "dolas" not in normalized_values


def test_plain_multi_places_skips_short_noise_fragments():
    items = _extract_plain_multi_places("kad yden maltepe gezi plani")
    assert "kad" not in items
    assert "yden" not in items
    assert "maltepe" in items


def test_plural_named_istanbul_districts_are_not_singularized():
    items = _extract_plain_multi_places("Adalar Avcılar Esenler gez")
    assert items == ["adalar", "avcılar", "esenler"]


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
        strong_route_pair=True,
    )
    assert final_type == "route"
    assert final_conf >= 0.80
    assert meta["reason"] == "direction+confident-pair=>route"


def test_has_explicit_route_pattern_detects_plain_suffix_route():
    assert has_explicit_route_pattern("kadikoyden maltepeye") is True


def test_has_explicit_route_pattern_detects_apostrophe_route():
    assert has_explicit_route_pattern("kadıköy'den maltepe'ye") is True


def test_has_confident_route_pair_requires_distinct_from_to_candidates():
    detected_places = [
        {"place": "Kadıköy", "role_hint": "from", "similarity": 1.0, "match_source": "lookup-exact", "token_count": 1},
        {"place": "Maltepe", "role_hint": "to", "similarity": 1.0, "match_source": "lookup-exact", "token_count": 1},
    ]
    assert has_confident_route_pair(detected_places) is True


def test_has_confident_route_pair_rejects_weak_embedding_only_pair():
    detected_places = [
        {"place": "Kadıköy", "role_hint": "from", "similarity": 0.76, "match_source": "embedding-cache", "token_count": 1},
        {"place": "Maltepe", "role_hint": "to", "similarity": 0.79, "match_source": "embedding-cache", "token_count": 1},
    ]
    assert has_confident_route_pair(detected_places) is False


def test_istanbul_district_suffix_roots_are_known():
    cases = [
        ("Adalara", "adalar", "to"),
        ("Avcılardan", "avcılar", "from"),
        ("Başakşehire", "başakşehir", "to"),
        ("Bayrampaşaya", "bayrampaşa", "to"),
        ("Çekmeköyde", "çekmeköy", "loc"),
        ("Eyüpsultandan", "eyüpsultan", "from"),
        ("Sultanbeyliye", "sultanbeyli", "to"),
    ]

    for token, expected_stem, expected_role in cases:
        stem, role_hint = normalize_token_with_role(token)
        assert stem == expected_stem
        assert role_hint == expected_role


def test_place_database_contains_all_istanbul_districts_without_osm():
    db = PlaceDatabase(
        use_osm=False,
        seed_dynamic_cache=False,
        seed_local_places=False,
        seed_static_places=True,
        seed_user_locations=False,
    )
    missing = [district for district in ISTANBUL_DISTRICTS if db.resolve_lookup(district) is None]
    alias_missing = [
        alias
        for district, alias in ISTANBUL_DISTRICT_ASCII_ALIASES.items()
        if db.resolve_lookup(alias) is None
    ]

    assert missing == []
    assert alias_missing == []


def test_local_places_seed_contains_all_istanbul_districts():
    seeded_names = set(get_all_local_place_names(limit=5000, include_dynamic=False))
    missing = [district for district in ISTANBUL_DISTRICTS if district not in seeded_names]

    assert missing == []
    assert lookup_local_place("Başakşehir")["display_name"] == "Başakşehir, İstanbul, Türkiye"


def test_should_rescue_poi_intent_when_single_location_and_poi_cue():
    assert should_rescue_poi_intent(
        query_type="route",
        has_poi_cue=True,
        poi_question_cue=False,
        route_intent_cue=False,
        direction_hints=False,
        role_hints={"loc"},
        unique_place_count=1,
    )


def test_should_not_rescue_poi_intent_when_route_direction_is_strong():
    assert not should_rescue_poi_intent(
        query_type="route",
        has_poi_cue=True,
        poi_question_cue=True,
        route_intent_cue=True,
        direction_hints=True,
        role_hints={"from", "to"},
        unique_place_count=2,
    )


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


def test_extract_places_uses_batch_encoding_instead_of_per_span_encode():
    class _StubBert:
        def __init__(self):
            self.encode_calls = 0
            self.encode_batch_calls = 0

        def encode(self, _text):
            self.encode_calls += 1
            return np.array([1.0, 0.0], dtype=np.float32)

        def encode_batch(self, texts):
            self.encode_batch_calls += 1
            return [np.array([1.0, 0.0], dtype=np.float32) for _ in texts]

    class _StubPlaces:
        def __init__(self):
            self._osm_prefetch_max_queries = 3
            self.find_calls = 0

        def prefetch_osm_candidates(self, *_args, **_kwargs):
            return 0

        def find_best_match(self, query, query_embedding, threshold, bert_engine, allow_below_threshold=False):
            self.find_calls += 1
            return {
                "place": query,
                "similarity": 0.95,
                "index": 0,
                "source": "embedding-cache",
            }

        def resolve_lookup(self, _token):
            return None

    engine = bert_module.BertNLPEngine.__new__(bert_module.BertNLPEngine)
    engine.bert = _StubBert()
    engine.places = _StubPlaces()
    engine._max_candidate_spans = 24

    places = engine.extract_places("Kadikoy'den Besiktas'a rota")
    assert isinstance(places, list)
    assert engine.bert.encode_batch_calls == 1
    assert engine.bert.encode_calls == 0
    assert engine.places.find_calls >= 1


def test_extract_places_respects_span_cap():
    class _StubBert:
        def encode_batch(self, texts):
            return [np.array([1.0, 0.0], dtype=np.float32) for _ in texts]

    class _StubPlaces:
        def __init__(self):
            self._osm_prefetch_max_queries = 3
            self.find_calls = 0

        def prefetch_osm_candidates(self, *_args, **_kwargs):
            return 0

        def find_best_match(self, query, query_embedding, threshold, bert_engine, allow_below_threshold=False):
            self.find_calls += 1
            return {
                "place": query,
                "similarity": 0.95,
                "index": 0,
                "source": "embedding-cache",
            }

        def resolve_lookup(self, _token):
            return None

    engine = bert_module.BertNLPEngine.__new__(bert_module.BertNLPEngine)
    engine.bert = _StubBert()
    engine.places = _StubPlaces()
    engine._max_candidate_spans = 2

    _ = engine.extract_places("kadikoy besiktas uskudar taksim maltepe")
    assert engine.places.find_calls == 2


def test_extract_places_collapses_same_signature_candidates(monkeypatch):
    class _StubBert:
        def encode_batch(self, texts):
            return [np.array([1.0, 0.0], dtype=np.float32) for _ in texts]

    class _StubPlaces:
        def __init__(self):
            self._osm_prefetch_max_queries = 3
            self.calls = 0

        def prefetch_osm_candidates(self, *_args, **_kwargs):
            return 0

        def find_best_match(self, query, query_embedding, threshold, bert_engine, allow_below_threshold=False):
            self.calls += 1
            if self.calls == 1:
                return {
                    "place": "Maltepe",
                    "similarity": 0.94,
                    "index": 0,
                    "source": "embedding-cache",
                }
            return {
                "place": "Istanbul Maltepe",
                "similarity": 0.92,
                "index": 1,
                "source": "lookup-exact",
            }

        def resolve_lookup(self, _token):
            return None

    monkeypatch.setattr(
        bert_module,
        "extract_candidate_spans",
        lambda *_args, **_kwargs: [
            {
                "surface": "maltepeye",
                "normalized": "maltepe",
                "start": 0,
                "end": 9,
                "role_hint": "to",
                "token_count": 1,
            },
            {
                "surface": "maltepe'ye",
                "normalized": "maltepe",
                "start": 0,
                "end": 9,
                "role_hint": "to",
                "token_count": 1,
            },
        ],
    )

    engine = bert_module.BertNLPEngine.__new__(bert_module.BertNLPEngine)
    engine.bert = _StubBert()
    engine.places = _StubPlaces()
    engine._max_candidate_spans = 24

    places = engine.extract_places("maltepeye")

    assert len(places) == 1
    assert places[0]["place"] == "Istanbul Maltepe"
    assert places[0]["match_source"] == "lookup-exact"


def test_parse_rescues_plain_direction_pair_to_route(monkeypatch):
    engine = bert_module.BertNLPEngine.__new__(bert_module.BertNLPEngine)
    engine.classify_query_type_with_scores = lambda _query: (
        "multi",
        0.79,
        {"route": 0.84, "poi": 0.82, "multi": 0.85, "single": 0.83},
    )
    engine.extract_places = lambda _query, trace=None: [
        {
            "place": "Kadıköy",
            "similarity": 1.0,
            "start": 0,
            "end": 10,
            "role_hint": "from",
            "token_count": 1,
            "normalized": "kadıköy",
            "surface": "kadikoyden",
            "match_source": "lookup-exact",
        },
        {
            "place": "Maltepe",
            "similarity": 1.0,
            "start": 11,
            "end": 20,
            "role_hint": "to",
            "token_count": 1,
            "normalized": "maltepe",
            "surface": "maltepeye",
            "match_source": "lookup-exact",
        },
    ]
    engine.detect_route_direction = lambda _query, _places: {"origin": "Kadıköy", "destination": "Maltepe"}
    monkeypatch.setattr(bert_module, "extract_poi_concept_with_meta", lambda *_args, **_kwargs: {
        "concept": "",
        "osm_queries": [],
        "source": "unknown",
        "confidence": 0.0,
        "status": "unknown",
        "tokens": [],
        "candidates": [],
        "debug_plan": {},
    })

    result = engine.parse("kadikoyden maltepeye", include_trace=True)

    assert result["type"] == "route"
    assert result["origin"] == "Kadıköy"
    assert result["destination"] == "Maltepe"
    assert result["trace"]["intent_conflict_matrix"]["reason"] in {
        "direction+confident-pair=>route",
        "multi-to-route-rescue",
        "route-pattern",
    }


def test_parse_keeps_unknown_when_direction_pair_is_not_confident(monkeypatch):
    engine = bert_module.BertNLPEngine.__new__(bert_module.BertNLPEngine)
    engine.classify_query_type_with_scores = lambda _query: (
        "unknown",
        0.46,
        {"route": 0.48, "poi": 0.44, "multi": 0.47, "single": 0.45},
    )
    engine.extract_places = lambda _query, trace=None: [
        {
            "place": "Kabadüz",
            "similarity": 0.76,
            "start": 0,
            "end": 10,
            "role_hint": "from",
            "token_count": 1,
            "normalized": "kadıköy",
            "surface": "kadıköyden",
            "match_source": "embedding-cache",
        },
        {
            "place": "Maltepe",
            "similarity": 0.79,
            "start": 11,
            "end": 20,
            "role_hint": "to",
            "token_count": 1,
            "normalized": "maltepe",
            "surface": "maltepeye",
            "match_source": "embedding-cache",
        },
    ]
    engine.detect_route_direction = lambda _query, _places: {"origin": "Kabadüz", "destination": "Maltepe"}
    monkeypatch.setattr(bert_module, "extract_poi_concept_with_meta", lambda *_args, **_kwargs: {
        "concept": "",
        "osm_queries": [],
        "source": "unknown",
        "confidence": 0.0,
        "status": "unknown",
        "tokens": [],
        "candidates": [],
        "debug_plan": {},
    })

    result = engine.parse("kadıköyden maltepeye", include_trace=True)

    assert result["type"] == "unknown"
    assert result["error"] == "Sorgu anlaşılamadı"


def test_cache_osm_results_incremental_embedding_append(monkeypatch):
    class _FakeBert:
        def __init__(self):
            self.calls = 0

        def encode_batch(self, texts):
            self.calls += 1
            out = []
            for idx, text in enumerate(texts):
                base = float((len(text) % 7) + idx + 1)
                out.append(np.array([base, base + 0.5], dtype=np.float32))
            return out

    class _FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return [
                {"display_name": "Besiktas, Istanbul, Turkey", "lat": "41.043", "lon": "29.005"},
                {"display_name": "Taksim, Istanbul, Turkey", "lat": "41.036", "lon": "28.986"},
            ]

    db = PlaceDatabase(
        use_osm=True,
        prefer_osm_first=False,
        seed_dynamic_cache=False,
        seed_local_places=False,
        seed_static_places=False,
        seed_user_locations=False,
    )
    db.add_place("Kadikoy", embedding=np.array([1.0, 1.5], dtype=np.float32))
    db._embeddings = np.array([[1.0, 1.5]], dtype=np.float32)
    db._embedding_matrix_dirty = False
    db.OSM_RATE_LIMIT = 0.0

    monkeypatch.setattr(bert_module, "_osm_retry_request", lambda *_args, **_kwargs: _FakeResponse())
    monkeypatch.setattr(bert_module, "save_dynamic_place", lambda **_kwargs: None)
    monkeypatch.setattr(bert_module.time, "sleep", lambda *_args, **_kwargs: None)

    fake_bert = _FakeBert()
    added = db.cache_osm_results("besiktas taksim", bert_engine=fake_bert)

    assert added == 2
    assert fake_bert.calls >= 1
    assert db._embeddings.shape[0] == 3
    assert db._embedding_matrix_dirty is False
    assert db._place_name_to_index["Besiktas"] >= 0
    assert db._place_name_to_index["Taksim"] >= 0


def test_bert_gold_dataset_has_required_structure_and_unique_ids():
    rows = _load_gold_examples()
    ids = [row["id"] for row in rows]

    assert GOLD_DATA_PATH.exists()
    assert len(rows) >= 84
    assert len(ids) == len(set(ids))

    for row in rows:
        assert isinstance(row.get("query"), str) and row["query"].strip()
        assert isinstance(row.get("expected"), dict) and row["expected"].get("type")
        assert isinstance(row.get("tags"), list) and row["tags"]

        expected_type = row["expected"]["type"]
        if expected_type == "route":
            assert row["expected"].get("origin")
            assert row["expected"].get("destination")
        elif expected_type == "poi":
            assert row["expected"].get("location")
        elif expected_type == "single":
            assert row["expected"].get("destination")
        elif expected_type == "multi":
            assert isinstance(row["expected"].get("locations"), list)
            assert row["expected"]["locations"]


def test_bert_gold_dataset_meets_edge_case_coverage_thresholds():
    rows = _load_gold_examples()
    intent_counts = Counter(row["expected"]["type"] for row in rows)
    all_tags = {tag for row in rows for tag in row["tags"]}
    safety_bucket_count = sum(
        1
        for row in rows
        if set(row["tags"]) & {"scope", "false-positive", "mixed-intent", "unknown-chitchat", "route-ambiguous"}
    )

    assert intent_counts["route"] >= 10
    assert intent_counts["poi"] >= 10
    assert intent_counts["single"] >= 10
    assert intent_counts["multi"] >= 10
    assert safety_bucket_count >= 12
    assert REQUIRED_GOLD_TAGS.issubset(all_tags)


def test_bert_gold_dataset_real_parser_regression(monkeypatch):
    monkeypatch.setenv("ORP_BERT_USE_OSM", "0")
    monkeypatch.setenv("ORP_BERT_SEED_DYNAMIC", "0")

    engine = get_bert_nlp_engine()
    failures = []

    for row in _load_gold_examples():
        expected = row["expected"]
        result = engine.parse(row["query"], include_trace=False)
        expected_type = expected["type"]
        mismatch = result.get("type") != expected_type

        if not mismatch and expected_type == "route":
            mismatch = not (
                _place_matches_expected(result.get("origin"), expected.get("origin"))
                and _place_matches_expected(result.get("destination"), expected.get("destination"))
            )
        elif not mismatch and expected_type == "poi":
            mismatch = not _place_matches_expected(result.get("location"), expected.get("location"))
        elif not mismatch and expected_type == "single":
            mismatch = not _place_matches_expected(result.get("destination"), expected.get("destination"))
        elif not mismatch and expected_type == "multi":
            actual_locations = result.get("locations") or []
            expected_locations = expected.get("locations") or []
            mismatch = (
                len(actual_locations) != len(expected_locations)
                or any(
                    not _place_matches_expected(actual, wanted)
                    for actual, wanted in zip(actual_locations, expected_locations)
                )
            )

        if mismatch:
            failures.append({
                "id": row["id"],
                "query": row["query"],
                "expected": expected,
                "actual": {
                    "type": result.get("type"),
                    "origin": result.get("origin"),
                    "destination": result.get("destination"),
                    "location": result.get("location"),
                    "locations": result.get("locations"),
                    "error": result.get("error"),
                },
            })

    assert failures == []
