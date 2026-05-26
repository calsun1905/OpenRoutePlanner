"""
POI concept resolver tests (faz-1).
"""

import os
import sys

backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

from nlp_concept_resolver import (
    resolve_poi_concept,
    resolve_poi_from_tokens,
    extract_candidates,
    normalize_poi_concept,
    resolve_query,
    map_concept_to_osm_queries,
)
from bert_nlp_engine import extract_poi_concept_with_meta


def test_resolve_plural_case_suffix_to_pilavci():
    res = resolve_poi_concept("pilavcılardan")
    assert res.status == "success"
    assert res.concept == "pilavcı"
    assert res.source in {"morph+dict", "rule+dict"}


def test_resolve_latinized_variant_to_pilavci():
    res = resolve_poi_concept("pilavci")
    assert res.status == "success"
    assert res.concept == "pilavcı"


def test_unknown_surface_stays_unknown():
    res = resolve_poi_concept("zıplankafe")
    assert res.status == "unknown"
    assert res.concept is None


def test_extract_poi_concept_with_meta_ignores_location_span():
    meta = extract_poi_concept_with_meta(
        "küçükyalıda pilavcılardan arıyorum",
        detected_places=[{"start": 0, "end": 10}],
    )
    assert meta["concept"] == "pilavcı"
    assert meta["status"] == "success"


def test_resolve_from_tokens_prefers_multiword_when_exists():
    res = resolve_poi_from_tokens(["pilav", "salonu", "arıyorum"])
    assert res.status == "success"
    assert res.concept in {"pilav salonu", "pilavcı"}


def test_extract_candidates_contains_morph_forms():
    cands = extract_candidates("malatyada pilavcılardan iyi yer")
    assert any(c.startswith("pilav") for c in cands)


def test_normalize_poi_concept_returns_canonical():
    assert normalize_poi_concept("pilavcılardan") == "pilavcı"


def test_resolve_query_returns_osm_queries():
    plan = resolve_query("malatyada pilavcı arıyorum")
    assert plan["status"] == "success"
    assert plan["concept"] == "pilavcı"
    assert isinstance(plan["osm_queries"], list)
    assert plan["osm_queries"]


def test_map_concept_to_osm_queries_fallback_name():
    queries = map_concept_to_osm_queries("xzy-bilinmeyen")
    assert queries == [{"name": "xzy bilinmeyen"}]


def test_turkish_casing_resolves_firin():
    res = resolve_poi_concept("FIRIN")
    assert res.status == "success"
    assert res.concept == "fırın"
