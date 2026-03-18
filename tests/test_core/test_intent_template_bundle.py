"""
Intent template bundle ve hard-negative karar yardimcisi testleri.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
sys.path.insert(0, backend_dir)

from bert_nlp_engine import (  # noqa: E402
    load_intent_template_bundle,
    should_force_unknown_with_hard_negative,
)


def test_load_intent_template_bundle_from_file():
    payload = {
        "templates": {
            "route": ["A'dan B'ye rota"],
            "poi": ["Kadikoy'de kahve ara"],
            "multi": ["Kadikoy, Besiktas ve Uskudar gezisi"],
            "single": ["Taksim'e git"],
        },
        "hard_negatives": ["merhaba nasilsin", "yardim eder misin"],
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "bundle.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        templates, hard_negatives = load_intent_template_bundle(str(path))

    assert templates["route"] == ["A'dan B'ye rota"]
    assert templates["poi"] == ["Kadikoy'de kahve ara"]
    assert "merhaba nasilsin" in hard_negatives


def test_should_force_unknown_with_hard_negative_true():
    assert should_force_unknown_with_hard_negative(
        best_score=0.78,
        second_best_score=0.69,
        hard_negative_score=0.80,
    ) is True


def test_should_force_unknown_with_hard_negative_false():
    assert should_force_unknown_with_hard_negative(
        best_score=0.86,
        second_best_score=0.70,
        hard_negative_score=0.80,
    ) is False
