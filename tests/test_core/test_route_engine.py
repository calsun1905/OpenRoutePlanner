"""
Route Engine Unit Tests

Rota motoru temel fonksiyonlarının birim testleri.
"""

import pytest
import sys
import os

# Backend modüllerini path'e ekle
backend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, backend_dir)


class TestOverlapThresholds:
    """Overlap threshold fonksiyonu testleri"""

    def test_overlap_very_short_distance(self):
        """Çok kısa mesafe (< 1km) overlap threshold"""
        from route_engine import get_overlap_threshold
        result = get_overlap_threshold(0.5)
        assert result == 0.90

    def test_overlap_short_distance(self):
        """Kısa mesafe (1-3km) overlap threshold"""
        from route_engine import get_overlap_threshold
        result = get_overlap_threshold(2.0)
        assert result == 0.80

    def test_overlap_medium_distance(self):
        """Orta mesafe (3-7km) overlap threshold"""
        from route_engine import get_overlap_threshold
        result = get_overlap_threshold(5.0)
        assert result == 0.75

    def test_overlap_long_distance(self):
        """Uzun mesafe (> 7km) overlap threshold"""
        from route_engine import get_overlap_threshold
        result = get_overlap_threshold(10.0)
        assert result == 0.70


class TestMaxCandidates:
    """Maksimum aday sayısı fonksiyonu testleri"""

    def test_max_candidates_very_short(self):
        """Çok kısa mesafe (< 1km) max candidates"""
        from route_engine import get_max_candidates
        result = get_max_candidates(0.5)
        assert result == 50

    def test_max_candidates_short(self):
        """Kısa mesafe (1-3km) max candidates"""
        from route_engine import get_max_candidates
        result = get_max_candidates(2.0)
        assert result == 75

    def test_max_candidates_medium(self):
        """Orta mesafe (3-7km) max candidates"""
        from route_engine import get_max_candidates
        result = get_max_candidates(5.0)
        assert result == 100

    def test_max_candidates_long(self):
        """Uzun mesafe (> 7km) max candidates"""
        from route_engine import get_max_candidates
        result = get_max_candidates(10.0)
        assert result == 150


class TestConfigIntegration:
    """Config entegrasyon testleri"""

    def test_walk_speed_from_config(self):
        """Walk speed değeri config'den geliyor mu?"""
        from route_engine import ROUTE_CONFIG
        assert 'WALK_SPEED_KMH' in ROUTE_CONFIG
        assert ROUTE_CONFIG['WALK_SPEED_KMH'] == 5.0

    def test_overlap_thresholds_in_config(self):
        """Overlap threshold değerleri config'de mevcut mu?"""
        from route_engine import ROUTE_CONFIG
        assert 'OVERLAP_THRESHOLD_SHORT' in ROUTE_CONFIG
        assert 'OVERLAP_THRESHOLD_MEDIUM' in ROUTE_CONFIG
        assert 'OVERLAP_THRESHOLD_LONG' in ROUTE_CONFIG
        assert 'OVERLAP_THRESHOLD_VERY_LONG' in ROUTE_CONFIG

    def test_max_candidates_in_config(self):
        """Max candidates değerleri config'de mevcut mu?"""
        from route_engine import ROUTE_CONFIG
        assert 'MAX_CANDIDATES_VERY_SHORT' in ROUTE_CONFIG
        assert 'MAX_CANDIDATES_SHORT' in ROUTE_CONFIG
        assert 'MAX_CANDIDATES_LONG' in ROUTE_CONFIG
        assert 'MAX_CANDIDATES_VERY_LONG' in ROUTE_CONFIG

    def test_penalty_factor_in_config(self):
        """Penalty factor değeri config'de mevcut mu?"""
        from route_engine import ROUTE_CONFIG
        assert 'PENALTY_FACTOR' in ROUTE_CONFIG
        assert ROUTE_CONFIG['PENALTY_FACTOR'] == 2.0


class TestEdgeOverlap:
    """Kenar overlap hesaplama testleri"""

    def test_no_overlap(self):
        """Hiç overlap yok"""
        from route_engine import count_edge_overlap
        edges1 = [(1, 2), (2, 3), (3, 4)]
        edges2 = [(5, 6), (6, 7), (7, 8)]
        overlap = count_edge_overlap(edges1, edges2)
        assert overlap == 0.0

    def test_full_overlap(self):
        """Tam overlap"""
        from route_engine import count_edge_overlap
        edges1 = [(1, 2), (2, 3), (3, 4)]
        edges2 = [(1, 2), (2, 3), (3, 4)]
        overlap = count_edge_overlap(edges1, edges2)
        assert overlap == 1.0

    def test_partial_overlap(self):
        """Kısmi overlap"""
        from route_engine import count_edge_overlap
        edges1 = [(1, 2), (2, 3), (3, 4), (4, 5)]
        edges2 = [(2, 3), (3, 4)]
        overlap = count_edge_overlap(edges1, edges2)
        assert 0.0 < overlap < 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
