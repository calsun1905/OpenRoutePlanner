"""
Regex NLP fallback POI resolver integration tests.
"""

import os
import sys

backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

from nlp_engine import parse_query


def test_parse_query_poi_with_location_and_search_phrase():
    result = parse_query("Malatya'da pilavcı arıyorum")
    assert result["type"] == "poi"
    assert result.get("location")
    assert result.get("poi_concept") == "pilavcı"


def test_parse_query_poi_with_recommendation_phrase():
    result = parse_query("Küçükyalıda pilavcı önerir misin")
    assert result["type"] == "poi"
    assert result.get("poi_concept") == "pilavcı"
