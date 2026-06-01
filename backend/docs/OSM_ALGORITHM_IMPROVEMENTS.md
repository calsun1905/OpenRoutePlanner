# OSM Entegrasyonu ve Algoritma İyileştirme Önerileri

## 1. Graf Optimizasyonu

### 1.1 Rotalama Profili Filtreleme
```python
# OSM'den sadece yürünebilir yolları al
def filter_walkable_edges(G):
    """Sadece yürüyüş için uygun yolları tut"""
    walkable_highways = {
        'footway', 'path', 'pedestrian', 'steps',
        'living_street', 'residential', 'unclassified'
    }
    
    # Tehlikeli yolları filtrele
    avoid_highways = {'motorway', 'trunk', 'motorway_link'}
    
    edges_to_remove = []
    for u, v, data in G.edges(data=True):
        highway = data.get('highway', '')
        if highway in avoid_highways:
            edges_to_remove.append((u, v))
        elif highway not in walkable_highways:
            edges_to_remove.append((u, v))
    
    G.remove_edges_from(edges_to_remove)
    return G
```

### 1.2 Graf Sıkıştırma (Contracted Graph)
```python
# Çok kısa segmentleri birleştir (osm2po st 덧붙였다)
def contract_graph(G, min_segment_length=5.0):
    """Kısa segmentleri birleştir - daha az node = daha hızlı Dijkstra"""
    # Dead-end node'ları (degree=1) ve degree=2 olanları collapse et
    pass
```

---

## 2. Algoritma İyileştirmeleri

### 2.1 Hiyerarşik Dijkstra (Contraction Hierarchies - CH)
```python
def hierarchical_dijkstra(G, origin, dest):
    """
    OSM için ideal: CH + A* kombinasyonu
    - Önce highway'leri sırala (motorway > trunk > primary > ...)
    - Üst seviye yollardan kısayol bul
    - Sonra yerel yollara in
    """
    highway_priority = {
        'motorway': 100, 'trunk': 90, 'primary': 70,
        'secondary': 50, 'tertiary': 30, 'residential': 10
    }
    
    def highway_astar_heuristic(node):
        # Ana yollara yakınlık = düşük heuristic = hızlı
        pass
```

### 2.2 OSRM Tarzı Alternatif Yol Üretimi
```python
# Google Maps/OSRM'ın kullandığı yöntem:
# 1. k-directly-connected paths
# 2. k-staleness-free paths  
# 3. k-shortest path trees (k-SPT)

def osrm_alternative_routes(G, origin, dest, k=3):
    """
    OSRM'ın alternative_direction_gap algoritması:
    - İlk rotadan X derece farklı olmalı
    - Uzunluk farkı Y%'yi geçmemeli
    """
    # 1. Shortest path
    primary = nx.shortest_path(G, origin, dest, weight='length')
    
    # 2. Penalty ile alternatifler
    alternatives = []
    used_edges = path_to_edges(G, primary)
    
    for i in range(k):
        G_penalty = apply_penalty_to_graph(G, used_edges, penalty_factor=2.0)
        alt = nx.shortest_path(G_penalty, origin, dest, weight='penalty_length')
        
        # Açı farkını kontrol et
        if check_angle_difference(primary, alt) > 30:  # 30 derece fark
            alternatives.append(alt)
            used_edges.extend(path_to_edges(G, alt))
    
    return [primary] + alternatives
```

### 2.3 Multi-Level Dijkstra
```python
def multi_level_dijkstra(G, origin, dest):
    """
    3 seviyeli OSM yaklaşımı:
    L1: Yerel yollar (footway, path)
    L2: Mahalle bağlantıları (residential, tertiary)
    L3: Ana yollar (primary, secondary)
    """
    # L3'ten kısayol bul
    # L2 ile detaylandır
    # L1 ile son noktaya bağla
    pass
```

---

## 3. OSM Veri Kalitesi İyileştirmeleri

### 3.1 Oneway Düzeltmesi
```python
def fix_osm_directional_edges(G):
    """OSM oneway=yes tag'lerini düzgün uygula"""
    for u, v, data in G.edges(data=True, keys=True):
        if data.get('oneway') == 'yes':
            # Ters yön kenarı ekleme
            pass
        elif data.get('oneway') == '-1':
            # Tersine döndür
            pass
```

### 3.2 Walking Restrictions
```python
WALKING_RESTRICTIONS = {
    'foot': ['no', 'private', 'license'],
    'access': ['no', 'private', 'license'],
}

def check_walkable(G, u, v, data):
    foot = data.get('foot', 'yes')
    access = data.get('access', 'yes')
    
    if foot in WALKING_RESTRICTIONS['foot']:
        return False
    if access in WALKING_RESTRICTIONS['access']:
        return False
    
    # Tekstilere izin ver
    if data.get('highway') == 'steps':
        return True
        
    return True
```

---

## 4. Performans Optimizasyonları

### 4.1 Graph Caching
```python
# Önbelleğe alınmış graf kullan
from functools import lru_cache

@lru_cache(maxsize=10)
def get_cached_graph(lat, lon, radius):
    """Aynı bölge için grafı yeniden indirme"""
    return download_osm_graph(lat, lon, radius)
```

### 4.2 Batch Distance Matrix
```python
# Tüm mesafeleri bir kerede hesapla (TSP için)
def precompute_distance_matrix(G, nodes):
    """Distance matrix'i önceden hesapla - O(n²)"""
    import numpy as np
    n = len(nodes)
    dist_matrix = np.full((n, n), np.inf)
    
    for i in range(n):
        for j in range(i+1, n):
            try:
                d = nx.shortest_path_length(G, nodes[i], nodes[j], weight='length')
                dist_matrix[i][j] = d
                dist_matrix[j][i] = d
            except nx.NetworkXNoPath:
                pass
    
    return dist_matrix
```

---

## 5. Hata Yönetimi İyileştirmeleri

### 5.1 Graceful Degradation
```python
def robust_shortest_path(G, origin, dest):
    """
    Farklı ağırlıklar ile fallback stratejisi
    """
    strategies = [
        ('length', 'duration'),  # Önce mesafe, sonra süre
        ('duration', 'length'),  # Önce süre
        ('length',),            # Sadece mesafe
    ]
    
    for weights in strategies:
        try:
            if len(weights) == 1:
                return nx.shortest_path(G, origin, dest, weight=weights[0])
            else:
                # Birden fazla ağırlık kombinasyonu
                pass
        except nx.NetworkXNoPath:
            continue
    
    # Son çare: A* ile hafif relaxasyon
    return astar_path_with_relaxation(G, origin, dest)
```

---

## 6. Yapılacaklar Listesi (Öncelik Sırası)

| Öncelik | Yapılacak | Tahmini Süre |
|---------|-----------|-------------|
| 🔴 P1 | Graf filtreleme (sadece yürünebilir) | 2 saat |
| 🔴 P1 | Oneway/directional düzeltme | 1 saat |
| 🟡 P2 | Hiyerarşik Dijkstra (CH) | 8 saat |
| 🟡 P2 | Distance matrix precompute | 2 saat |
| 🟢 P3 | OSRM tarzı alternatif rotalar | 6 saat |
| 🟢 P3 | Graph caching | 1 saat |
