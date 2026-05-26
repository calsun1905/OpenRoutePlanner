# Deniz Kıyısı Rotalama Problemleri - Analiz Raporu

## Gözlemlenen Problemler

### 1. Köprü Tercih Etmeme Problemi
**Problem:** Deniz kıyısında yürürken köprü yerine sahil yolunu tercih etmek isteniyor ama algoritma köprüyü seçiyor.

**Kök Neden:** 
- OSM'de `bridge=yes` tag'i var ama **sahil yolu** ile **köprü** arasında otomatik bir öncelik yok
- Mevcut kod sadece `network_type="walk"` kullanıyor - tüm yürünebilir yollar eşit

### 2. Başlangıç Noktası Problemi  
**Problem:** Tam olarak nokta konulan yerlerden bazen rota başlamıyor veya farklı bir yere snap ediliyor.

**Kök Neden:**
- `find_nearest_node()` fonksiyonu en yakın yol kenarına snap ediyor (satır 464-468)
- Eğer kullanıcı bir iskeleye veya kıyıya yakınsa, en yakın OSM node'a değil snap edilebilir
- OSM node'ları bazen denize uzanmış iskelelerde olabilir

---

## Mevcut Kod Analizi

### graph_manager.py - Graf İndirme (satır 316)
```python
G = ox.graph_from_place(place_name, network_type="walk")
```
**Sorun:** `network_type="walk"` tüm köprüleri ve iskeleleri dahil eder - hiçbir ayrım yapmaz.

### graph_manager.py - _filter_outdoor_walk_graph (satır 278-299)
```python
def _is_blocked_walk_edge(data: dict) -> bool:
    tunnel_values = _osm_values(data.get("tunnel"))
    if any("building_passage" in value for value in tunnel_values):
        return True
    # ... diğer filtreler
```
**Sorun:** Köprüler için **hiçbir filtre yok**!

### graph_manager.py - find_nearest_node (satır 461-472)
```python
def find_nearest_node_with_distance(G, lat: float, lon: float) -> tuple[int, float]:
    try:
        u, v, key = ox.nearest_edges(G, X=lon, Y=lat)  # En yakın kenarı bul
        dist_u = _distance_to_node_m(G, u, lat, lon)
        dist_v = _distance_to_node_m(G, v, lat, lon)
        node_id = u if dist_u <= dist_v else v  # En yakın node'a snap
```
**Sorun:** Sadece mesafeye bakıyor - köprü mü, sahil mi ayrımı yok.

---

## Çözüm Önerileri

### Öneri 1: Köprü Cezalandırma
```python
def _bridge_penalty(data: dict) -> float:
    """Köprü kenarlarına ağırlık cezası uygula"""
    if data.get("bridge", "").lower() in ["yes", "viaduct"]:
        return BRIDGE_PENALTY_FACTOR  # 1.5 - 2.0
    return 1.0

# shortest_path çağrısında:
nx.shortest_path(G, origin, dest, weight="length")  
# yerine:
# Her kenar için: length * _bridge_penalty(data)
```

### Öneri 2: Kıyı Mesafesi Filtresi
```python
def distance_to_coast_m(lat: float, lon: float) -> float:
    """Kıyı çizgisine mesafe (metre) - nominatim/overpass API gerekebilir"""
    # https://overpass-turbo.eu/ ile kıyı verisi çekilebilir
    pass

def avoid_coastal_bridges(G, max_coast_dist_m=50):
    """Kıyıya yakın köprüleri işaretle"""
    for u, v, key, data in G.edges(keys=True, data=True):
        if data.get("bridge"):
            # Node koordinatlarını al
            u_lat = G.nodes[u].get('y', 0)
            u_lon = G.nodes[u].get('x', 0)
            # Kıyıya mesafeyi kontrol et
            if distance_to_coast_m(u_lat, u_lon) < max_coast_dist_m:
                data["penalty_bridge"] = 10.0  # Çok ceza
```

### Öneri 3: Başlangıç Noktası İyileştirmesi
```python
def find_valid_start_node(G, lat: float, lon: float) -> int:
    """Kıyı/deniz uzantılarını filtreleyerek başla"""
    node_id = find_nearest_node(G, lat, lon)
    
    # Eğer bu node denizdeyse (osm_id < 0 veya tag kontrolü)
    node_data = G.nodes[node_id]
    if node_data.get("highway") == "pier":
        # En yakın kara node'u bul
        pass
    
    return node_id
```

---

## Öncelik Sırası

| Öncelik | Çözüm | Zorluk |
|---------|-------|--------|
| 🔴 P1 | Köprü cezası (penalty) | Kolay |
| 🟡 P2 | Kıyı mesafe API entegrasyonu | Orta |
| 🟢 P3 | Pier/isthmus node filtresi | Orta |

---

## Test Senaryoları

1. **Kadıköy - Moda sahili**: Köprü yerine deniz kenarı tercih edilmeli
2. **Beach başlangıç noktası**: Tam noktadan başlamalı, iskeleye snap etmemeli
3. **Bosphorus kıyısı**: Sahil yolu tercih edilmeli, köprüler cezalandırılmalı
