"""
BERT NLP preprocessing helper tests.

Bu testler model yüklemeden token normalizasyonu ve span çıkarım
davranışını doğrular.
"""

import os
import sys
import numpy as np


backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

import bert_nlp_engine as bert_module
from bert_nlp_engine import (
    extract_candidate_spans,
    normalize_token_with_role,
    is_likely_action_token,
    is_poi_concept_term,
    extract_poi_concept,
    apply_intent_conflict_matrix,
    should_rescue_poi_intent,
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
