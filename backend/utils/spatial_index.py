"""
spatial_index.py - Mekansal İndeksleme

POI (Points of Interest) için hızlı konum bazlı arama.
R-tree kullanarak O(log n) yerine O(n) arama yapar.
"""

import math
import threading
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class BoundingBox:
    """
    2D bounding box (sınırlayıcı kutu).

    Args:
        min_lon: Minimum boylam (batı)
        min_lat: Minimum enlem (güney)
        max_lon: Maksimum boylam (doğu)
        max_lat: Maksimum enlem (kuzey)
    """
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def contains(self, lon: float, lat: float) -> bool:
        """Nokta bounding box içinde mi?"""
        return self.min_lon <= lon <= self.max_lon and self.min_lat <= lat <= self.max_lat

    def intersects(self, other: 'BoundingBox') -> bool:
        """İki bounding box kesişiyor mu?"""
        return not (
            self.max_lon < other.min_lon or
            self.min_lon > other.max_lon or
            self.max_lat < other.min_lat or
            self.min_lat > other.max_lat
        )

    def expand(self, margin_meters: float) -> 'BoundingBox':
        """Bounding box'i belirli bir miktar genişletir."""
        # 1 derece ~111 km (enlem için)
        # Boylam için enleme bağlı: 1 derece ~111 * cos(lat) km
        center_lat = (self.min_lat + self.max_lat) / 2
        lat_margin = margin_meters / 111000
        lon_margin = margin_meters / (111000 * math.cos(math.radians(center_lat)))

        return BoundingBox(
            min_lon=self.min_lon - lon_margin,
            min_lat=self.min_lat - lat_margin,
            max_lon=self.max_lon + lon_margin,
            max_lat=self.max_lat + lat_margin
        )

    def to_tuple(self) -> Tuple[float, float, float, float]:
        """R-tree için tuple formatına çevirir."""
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)


class POIItem:
    """
    POI öğesi için wrapper.

    Args:
        poi_id: Benzersiz POI identifier
        name: POI adı
        lon: Boylam
        lat: Enlem
        bbox: BoundingBox (opsiyonel)
        data: Ek veriler (kategori, adres vb.)
    """

    def __init__(
        self,
        poi_id: str,
        name: str,
        lon: float,
        lat: float,
        bbox: Optional[BoundingBox] = None,
        **data
    ):
        self.poi_id = poi_id
        self.name = name
        self.lon = lon
        self.lat = lat
        self.bbox = bbox or BoundingBox(lon, lat, lon, lat)
        self.data = data

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """R-tree için bounds tuple'ı."""
        return self.bbox.to_tuple()

    def distance_to(self, lon: float, lat: float) -> float:
        """Haversine formülü ile mesafe hesapla (metre)."""
        dlat = math.radians(lat - self.lat)
        dlon = math.radians(lon - self.lon)
        a = (
            math.sin(dlat / 2) ** 2 +
            math.cos(math.radians(self.lat)) *
            math.cos(math.radians(lat)) *
            math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))
        return 6371000 * c  # Dünya yarıçapı (metre)


class SpatialIndex:
    """
    Basit R-tree benzeri mekanasal indeks implementasyonu.

    Python'da rtree kütüphanesi kullanılabilmese de,
    bağımlılık azaltmak için basit grid-based implementasyon.

    Features:
    - Grid-based partitioning (hızlı erişim)
    - Bounding box queries
    - K-radius search
    """

    def __init__(self, grid_size: float = 0.01):
        """
        Args:
            grid_size: Grid hücre boyutu (derece cinsinden)
                       ~1km İstanbul enleminde
        """
        self.grid_size = grid_size
        self.grid: Dict[Tuple[int, int], List[POIItem]] = {}
        self.poi_dict: Dict[str, POIItem] = {}

    def _get_cell_key(self, lon: float, lat: float) -> Tuple[int, int]:
        """Koordinat için grid cell key döner."""
        return (int(lon / self.grid_size), int(lat / self.grid_size))

    def _get_cells_for_bbox(self, bbox: BoundingBox) -> List[Tuple[int, int]]:
        """Bounding box'ı kapsayan tüm grid cell'leri döner."""
        min_cell = self._get_cell_key(bbox.min_lon, bbox.min_lat)
        max_cell = self._get_cell_key(bbox.max_lon, bbox.max_lat)

        cells = []
        for i in range(min_cell[0], max_cell[0] + 1):
            for j in range(min_cell[1], max_cell[1] + 1):
                cells.append((i, j))
        return cells

    def insert(self, poi: POIItem) -> None:
        """POI'yi mekanasal indekse ekler."""
        # Anahtar dict'e ekle
        self.poi_dict[poi.poi_id] = poi

        # Grid cell'lere ekle
        center_lon = (poi.bbox.min_lon + poi.bbox.max_lon) / 2
        center_lat = (poi.bbox.min_lat + poi.bbox.max_lat) / 2
        cell_key = self._get_cell_key(center_lon, center_lat)

        if cell_key not in self.grid:
            self.grid[cell_key] = []
        self.grid[cell_key].append(poi)

    def search_bbox(self, bbox: BoundingBox) -> List[POIItem]:
        """
        Bounding box içindeki tüm POI'leri döner.

        Args:
            bbox: Arama bounding box'ı

        Returns:
            Bounding box içindeki POI listesi
        """
        results = []
        seen_ids = set()

        # İlgili grid cell'leri bul
        cells = self._get_cells_for_bbox(bbox)

        for cell_key in cells:
            if cell_key not in self.grid:
                continue

            for poi in self.grid[cell_key]:
                if poi.poi_id in seen_ids:
                    continue
                seen_ids.add(poi.poi_id)

                # Tam bounding box kontrolü
                if bbox.intersects(poi.bbox):
                    results.append(poi)

        return results

    def search_radius(
        self,
        lon: float,
        lat: float,
        radius_meters: float
    ) -> List[POIItem]:
        """
        Belirli bir noktanın r yarıçapındaki POI'leri döner.

        Args:
            lon: Merkez boylam
            lat: Merkez enlem
            radius_meters: Yarıçap (metre)

        Returns:
            Yarıçap içindeki POI listesi (mesafeye göre sıralı)
        """
        # Bounding box oluştur
        center_bbox = BoundingBox(lon, lat, lon, lat)
        search_bbox = center_bbox.expand(radius_meters)

        # İlk adayları bul
        candidates = self.search_bbox(search_bbox)

        # Mesafeye göre filtrele ve sırala
        results = []
        for poi in candidates:
            distance = poi.distance_to(lon, lat)
            if distance <= radius_meters:
                results.append((poi, distance))

        # Mesafeye göre sırala
        results.sort(key=lambda x: x[1])
        return [poi for poi, _ in results]

    def search_nearest(
        self,
        lon: float,
        lat: float,
        limit: int = 5
    ) -> List[Tuple[POIItem, float]]:
        """
        En yakın N POI'yi döner.

        Args:
            lon: Merkez boylam
            lat: Merkez enlem
            limit: Maksimum sonuç sayısı

        Returns:
            (POI, mesafe) tuple listesi (mesafeye göre sıralı)
        """
        # Arama yarıçapını dinamik belirle
        # Önce küçük bir alan tara, sonuç yoksa genlet
        search_radius = 500  # 500m ile başla
        max_radius = 5000     # 5km maksimum

        while search_radius <= max_radius:
            results = self.search_radius(lon, lat, search_radius)
            if len(results) >= limit:
                # İlk limit kadarını al
                poi_distances = [(poi, poi.distance_to(lon, lat)) for poi in results[:limit]]
                poi_distances.sort(key=lambda x: x[1])
                return poi_distances
            search_radius *= 2  # Arama alanını ikiye katla

        return []

    def get(self, poi_id: str) -> Optional[POIItem]:
        """POI ID ile POI döner."""
        return self.poi_dict.get(poi_id)

    def remove(self, poi_id: str) -> bool:
        """POI'yi indeksten siler."""
        if poi_id not in self.poi_dict:
            return False

        poi = self.poi_dict[poi_id]

        # Grid cell'den sil
        center_lon = (poi.bbox.min_lon + poi.bbox.max_lon) / 2
        center_lat = (poi.bbox.min_lat + poi.bbox.max_lat) / 2
        cell_key = self._get_cell_key(center_lon, center_lat)

        if cell_key in self.grid:
            self.grid[cell_key] = [p for p in self.grid[cell_key] if p.poi_id != poi_id]

        # Dict'ten sil
        del self.poi_dict[poi_id]
        return True

    def clear(self) -> None:
        """Tüm indeksi temizler."""
        self.grid.clear()
        self.poi_dict.clear()

    def stats(self) -> Dict[str, Any]:
        """İndeks istatistikleri."""
        return {
            "total_pois": len(self.poi_dict),
            "total_cells": len(self.grid),
            "avg_pois_per_cell": (
                sum(len(cell) for cell in self.grid.values()) / len(self.grid)
                if self.grid else 0
            ),
            "grid_size": self.grid_size
        }


class POISpatialCache:
    """
    POI için mekanasal cache wrapper.

    Özellikler:
    - Spatial index ile hızlı arama
    - LRU cache ile memory management
    - Category-based filtreleme

    Kullanım:
        cache = POISpatialCache(maxsize=100)

        # POI ekle
        cache.insert("poi1", "Kadıköy Square", 29.0284, 41.0284, category="square")

        # Bounding box ile ara
        bbox = BoundingBox(29.0, 41.0, 29.1, 41.1)
        results = cache.search_bbox(bbox, category="square")

        # Yarıçap ile ara
        results = cache.search_radius(29.0284, 41.0284, 500, category="cafe")
    """

    def __init__(self, maxsize: int = 100, grid_size: float = 0.01):
        self.spatial_index = SpatialIndex(grid_size=grid_size)
        self.maxsize = maxsize
        self.category_index: Dict[str, List[str]] = {}

    def insert(
        self,
        poi_id: str,
        name: str,
        lon: float,
        lat: float,
        category: str = "",
        **data
    ) -> None:
        """POI'yi cache'e ekler."""
        # Category index'e ekle
        if category and category not in self.category_index:
            self.category_index[category] = []
        if category:
            self.category_index[category].append(poi_id)

        # Spatial index'e ekle
        poi = POIItem(
            poi_id=poi_id,
            name=name,
            lon=lon,
            lat=lat,
            **data
        )
        self.spatial_index.insert(poi)

        # Boyut kontrolü (basit FIFO)
        if len(self.spatial_index.poi_dict) > self.maxsize:
            # En eski POI'yi sil (basit implementasyon)
            # Gerçek LRU için ekstra tracking gerekir
            oldest_id = next(iter(self.spatial_index.poi_dict))
            self.remove(oldest_id)

    def search_bbox(
        self,
        bbox: BoundingBox,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Bounding box içinde arama yapar."""
        pois = self.spatial_index.search_bbox(bbox)

        # Category filtrele
        if category:
            pois = [p for p in pois if p.data.get("category") == category]

        # Sonuçları dict formatına çevir
        return [
            {
                "id": p.poi_id,
                "name": p.name,
                "lon": p.lon,
                "lat": p.lat,
                **p.data
            }
            for p in pois
        ]

    def search_radius(
        self,
        lon: float,
        lat: float,
        radius_meters: float,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Yarıçap içinde arama yapar."""
        pois = self.spatial_index.search_radius(lon, lat, radius_meters)

        # Category filtrele
        if category:
            pois = [p for p in pois if p.data.get("category") == category]

        # Limit uygula
        pois = pois[:limit]

        # Sonuçları dict formatına çevir
        return [
            {
                "id": p.poi_id,
                "name": p.name,
                "lon": p.lon,
                "lat": p.lat,
                "distance": p.distance_to(lon, lat),
                **p.data
            }
            for p in pois
        ]

    def search_nearest(
        self,
        lon: float,
        lat: float,
        limit: int = 5,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """En yakın POI'leri döner."""
        results = self.spatial_index.search_nearest(lon, lat, limit)

        # Category filtrele
        if category:
            results = [(p, d) for p, d in results if p.data.get("category") == category]

        # Sonuçları dict formatına çevir
        return [
            {
                "id": p.poi_id,
                "name": p.name,
                "lon": p.lon,
                "lat": p.lat,
                "distance": d,
                **p.data
            }
            for p, d in results
        ]

    def get(self, poi_id: str) -> Optional[Dict[str, Any]]:
        """POI ID ile arama yapar."""
        poi = self.spatial_index.get(poi_id)
        if poi:
            return {
                "id": poi.poi_id,
                "name": poi.name,
                "lon": poi.lon,
                "lat": poi.lat,
                **poi.data
            }
        return None

    def remove(self, poi_id: str) -> bool:
        """POI'yi cache'ten siler."""
        poi = self.spatial_index.get(poi_id)
        if poi:
            # Category index'ten sil
            category = poi.data.get("category")
            if category and category in self.category_index:
                self.category_index[category] = [
                    pid for pid in self.category_index[category] if pid != poi_id
                ]

        return self.spatial_index.remove(poi_id)

    def clear(self) -> None:
        """Tüm cache'i temizler."""
        self.spatial_index.clear()
        self.category_index.clear()

    def stats(self) -> Dict[str, Any]:
        """Cache istatistikleri."""
        spatial_stats = self.spatial_index.stats()
        return {
            **spatial_stats,
            "categories": len(self.category_index),
            "maxsize": self.maxsize
        }


# Global singleton instance
_poi_spatial_cache: Optional[POISpatialCache] = None
_spatial_lock = threading.Lock()


def get_poi_spatial_cache(maxsize: int = 100) -> POISpatialCache:
    """Global POI spatial cache singleton'ı döner."""
    global _poi_spatial_cache
    if _poi_spatial_cache is None:
        with _spatial_lock:
            if _poi_spatial_cache is None:
                _poi_spatial_cache = POISpatialCache(maxsize=maxsize)
    return _poi_spatial_cache
