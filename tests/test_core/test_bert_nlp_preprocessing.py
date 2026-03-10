"""
BERT NLP preprocessing helper tests.

Bu testler model yüklemeden token normalizasyonu ve span çıkarım
davranışını doğrular.
"""

import os
import sys


backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

from bert_nlp_engine import extract_candidate_spans, normalize_token_with_role


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
