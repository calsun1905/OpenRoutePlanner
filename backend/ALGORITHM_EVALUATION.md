# OpenRoutePlanner Yol Bulma Algoritmaları Değerlendirme Raporu

**Tarih:** 2026-05-26  
**Durum:** Tamamlandi

---

## Yönetici Özeti

Proje, İstanbul için çok katmanlı bir yol bulma sistemi sunmaktadır. Üç temel algoritma kategorisi mevcuttur:

1. **Yaya Yönlendirme** (OSMnx + NetworkX)
2. **Toplu Taşıma** (GTFS + İstanbul BB API)
3. **Çok Modlu Rota** (Multimodal Engine)

Sistem, endüstri standardı Via-Node yaklaşımı kullanarak alternatif rota üretimi yapabilmektedir.

---

## 1. Algoritmaların Detaylı İncelemesi

### 1.1 Dijkstra Algoritması (En Kısa Yol)

**Dosya:** [`route_engine_impl.py`](backend/route_engine_impl.py:60)  
**Fonksiyon:** `shortest_path()`

```python
path = nx.shortest_path(G, origin_node, dest_node, weight=_routing_weight_key())
```

**Değerlendirme:**
| Kriter | Durum | Açıklama |
|--------|-------|----------|
| Doğruluk | ✅ İyi | NetworkX'in optimize Dijkstra implementasyonu |
| Performans | ⚠️ Orta | Büyük grafiklerde (10K+ düğüm) yavaşlabilir |
| Oneway Desteği | ✅ Var | OSM verisi üzerinden doğal destek |

**Güçlü Yönler:**
- Güvenilir ve test edilmiş implementasyon
- Ağırlık attribute'u esnekliği (length, penalty_length, routing_length)

**Zayıf Yönler:**
- Aynı koordinata map eden çoklu noktalar için `node_to_index` çakışması riski (satır 181)
- Ulaşılamayan düğümler için `NetworkXNoPath` istisnası yönetimi yetersiz

---

### 1.2 TSP (Gezgin Satıcı Problemi)

**Dosya:** [`route_engine_impl.py`](backend/route_engine_impl.py:167)  
**Fonksiyon:** `solve_tsp()`

```python
tsp_route = traveling_salesman_problem(tsp_graph, weight="weight", cycle=False)
```

**Değerlendirme:**
| Kriter | Durum | Açıklama |
|--------|-------|----------|
| Doğruluk | ✅ İyi | NetworkX approximation (greedy farm arayüzü) |
| Performans | ⚠️ Orta | O(n²) mesafe matrisi hesaplaması |
| Kapsama | ⚠️ Sınırlı | 10+ noktada yavaş |

**Güçlü Yönler:**
- Çoklu nokta optimizasyonu
- Dinamik fallback: sıralı rota kullanımı

**Zayıf Yönler ve Bilinen Sorunlar (ALGORITHM_ISSUES.md):**

| Sorun | Öncelik | Satır | Açıklama |
|-------|---------|-------|----------|
| P1 | Ulaşılamayan düğümler için sonsuz ağırlık ataması | ~162-169 | TSP grafında kenar oluşturulmasına rağmen çözüm yanlış olabilir |
| P2 | Aynı node'a map eden noktalar | ~181 | `node_to_index` sözlüğünde sadece bir indeks kalır |
| P2 | Edge key ihmali | ~588-593 | Paralel kenarların tamamı cezalandırılabilir |

---

### 1.3 Via-Node Algoritması (Alternatif Rota Üretimi)

**Dosya:** [`route_engine_impl.py`](backend/route_engine_impl.py:831)  
**Fonksiyon:** `find_via_node_routes()`

**Değerlendirme:**
| Kriter | Durum | Açıklama |
|--------|-------|----------|
| Paradigma | ✅ İyi | Endüstri standardı (Google Maps/OSRM tarzı) |
| Stabilite | ⚠️ Orta | Node attribute eksikliğinde bounding box hatası |
| Performans | ⚠️ Orta | Bounding box genişletmesi + derece hesabı |

**Algoritma Adımları:**
1. Ana rota koordinatlarının bounding box'ını hesapla (satır 870-883)
2. Box içindeki yüksek dereceli node'ları bul (degree >= VIA_NODE_MIN_DEGREE)
3. Ana rotadan geometrik olarak en uzak olanları seç
4. A → via → B rotası oluştur
5. `max_distance_ratio` ile çok uzun rotaları reddet

**Zayıf Yönler (ALGORITHM_ISSUES.md):**
- **P2:** Node'larda 'y' veya 'x' attribute yoksa 0 kullanılıyor → bounding box nokta haline gelebilir (satır 788-790)
- **P2:** MultiDiGraph edge key ihmal edilmesi

---

### 1.4 Penalty-Based Generation

**Dosya:** [`route_engine_impl.py`](backend/route_engine_impl.py:632)  
**Fonksiyon:** `apply_penalty_to_graph()`, `find_routes_with_penalty()`

**Değerlendirme:**
| Kriter | Durum | Açıklama |
|--------|-------|----------|
| Temel Yaklaşım | ✅ İyi | Kullanılan kenarlara ceza ile farklı yol bulma |
| Gövde-Only Penalty | ✅ İyi | Baş/son %10'a dokunmama (v3.0 iyileştirmesi) |

**Güçlü Yönler:**
- `penalty_length` attribute ile doğrudan shortest_path kullanımı
- Body-edge penalty ile zikzak-engelleme

**Zayıf Yönler:**
- Penalty factor parametresi genellikle sabit (2.0)
- Birden fazla node pair için paralel kenarların tümü cezalandırılabilir

---

### 1.5 Edge Disjoint Paths (Menger Teoremi)

**Dosya:** [`route_engine_impl.py`](backend/route_engine_impl.py:522)  
**Fonksiyon:** `find_disjoint_paths()`

**Değerlendirme:**
| Kriter | Durum | Açıklama |
|--------|-------|----------|
| Teorik Temel | ✅ İyi | NetworkX edge_disjoint_paths |
| Pratik Kullanım | ⚠️ Sınırlı | OSM çıkmaz sokak senaryolarında yetersiz |

**Not:** v3.0'da Via-Node'a geçildiği için asıl kullanım artık daha az.

---

### 1.6 Multimodal Engine (Çok Modlu Rota)

**Dosya:** [`multimodal_engine.py`](backend/multimodal_engine.py:1)

**Değerlendirme:**
| Kriter | Durum | Açıklama |
|--------|-------|----------|
| OSRM Entegrasyonu | ✅ İyi | Road-level routing ile yol takip |
| Su Geçişi Koruması | ✅ Çok İyi | Boğaz/Halic için Guards |
| GTFS Verisi | ⚠️ Sınırlı | İstanbul BB API bağımlılığı |
| Performans | ⚠️ Orta | Çoklu API çağrıları |

**Temel Bileşenler:**

1. **OSRM Road Routing:**
   - `_osrm_route_coords()`: İki nokta arası yol koordinatları
   - `_osrm_multi_waypoint()`: Çoklu waypoint desteği
   - `_get_bus_road_coords()`: Duraklar arası yol

2. **Transit Seçenekler:**
   - Metro/Tram/Füniküler: `find_metro_transfer_pairs()`
   - Vapur: `FERRY_TERMINAL_LINKS` (satır 301)
   - Otobüs: `_get_nearby_routes()`

3. **Yürüme Bağlantıları:**
   - `_build_walk_leg()`: OSRM foot routing doğrulaması
   - Su geçişi kontrolleri

**Güçlü Yönler:**
- Marmaray entegrasyonu (virtual links)
- Boğaz geçişi için çok katmanlı koruma (`_is_forbidden_bosphorus_walk`)
- GTFS shapes ile metro güzergahı koordinatları

**Zayıf Yönler:**
- `UnicodeEncodeError` potansiyeli (Türkçe karakterler)
- Overpass API timeout senaryoları
- İstanbul BB API'nin güncel olmama riski

---

### 1.7 Graph Manager (OSM Veri Yönetimi)

**Dosya:** [`graph_manager.py`](backend/graph_manager.py:1)

**Değerlendirme:**
| Kriter | Durum | Açıklama |
|--------|-------|----------|
| OSMnx Entegrasyonu | ✅ İyi | graph_from_place + graph_from_point |
| Caching | ✅ Çok İyi | LRU + TTL stratejisi |
| POI Arama | ✅ İyi |(features_from_place) |

**Temel Fonksiyonlar:**

1. **Graf İndirme:**
   - `get_graph()`: Place-based indirme
   - `get_graph_for_points()`: Point-based (daha hızlı)

2. **Snap-to-Graph:**
   - `find_nearest_node_with_distance()`: Köprü cezalı snap
   - `_bosphorus_side()`: Boğaz tarafı tespiti

3. **Outdoor Routing Filtresi:**
   - `_filter_outdoor_walk_graph()`: İç mekan/özel yolları çıkarır
   - Köprü kenarlarını korur

---

## 2. Karşılaştırmalı Performans Analizi

### 2.1 Algoritma Karmaşıklıkları

| Algoritma | Zaman | Alan | Not |
|-----------|-------|------|-----|
| Dijkstra (shortest_path) | O(V log V + E) | O(V) | NetworkX optimized |
| TSP (NetworkX approx) | O(n² · m) | O(n²) | m = kenar sayısı |
| Via-Node | O(V + E) | O(V) | + BBox araması |
| Multimodal (Dijkstra + API) | Değişken | O(V) | API latency önemli |

### 2.2 Kullanım Senaryoları

| Senaryo | Önerilen Algoritma | Neden |
|---------|-------------------|-------|
| A noktasından B'ye kısa yol | Dijkstra | Hızlı, güvenilir |
| 5+ noktalı tur | TSP | Optimizasyon gerekli |
| Farklı güzergah önerileri | Via-Node + Penalty | En iyi çeşitlilik |
| Yaya + Metro kombinasyonu | Multimodal Engine | Çok modlu destek |
| Boğaz geçişi | Multimodal (Guard'lar) | Su geçişi kontrolü |

---

## 3. Bilinen Sorunlar ve Öncelik Sıralaması

### 3.1 Kritik Sorunlar (P1)

| # | Sorun | Dosya:Satır | Çözüm Önerisi |
|---|-------|-------------|--------------|
| 1 | Ulaşılamayan düğümler için TSP hatası | route_engine_impl.py:162-169 | Sonsuz ağırlıklı kenarları graf dışı bırak |
| 2 | Aynı node'a map eden çoklu noktalar | route_engine_impl.py:181 | Eksik indeks kontrolü ekle |

### 3.2 Orta Öncelikli Sorunlar (P2)

| # | Sorun | Dosya:Satır | Çözüm Önerisi |
|---|-------|-------------|--------------|
| 1 | Node attribute eksikliği | route_engine_impl.py:788-790 | Hata fırlat veya default bbox oluştur |
| 2 | MultiDiGraph edge key ihmali | route_engine_impl.py:588-593 | Tüm (u,v,key) kombinasyonlarını izle |
| 3 | Çok geniş exception yakalama | route_engine_impl.py:901 | Sadece bilinen hataları yakala |

### 3.3 Düşük Öncelikli Sorunlar (P3)

| # | Sorun | Not |
|---|-------|-----|
| 1 | successors/predecessors kontrolü | Test edilmesi gerekiyor |
| 2 | Çok kısa rotalarda BBox | min_margin ile çözüldü |
| 3 | Shapely geometri hataları | Kabul edilebilir fallback var |

---

## 4. Geliştirme Önerileri

### 4.1 Kısa Vadeli (1-2 hafta)

```
Öncelik 1: TSP düzeltmeleri
├── node_to_index çakışması için ek kontrol
└── dist_matrix sonsuz değerler için graf dışı bırakma

Öncelik 2: Via-Node stabilizasyonu  
├── Node attribute doğrulama
└── min_margin artırımı (0.002 → 0.003)
```

### 4.2 Orta Vadeli (1-2 ay)

```
Öncelik 1: Hiyerarşik Dijkstra (Contraction Hierarchies)
├── OSM highway'leri sırala
└── shortcut kenarlar ekle

Öncelik 2: Pareto optimal rotalar
├── Mesafe + Güvenlik + Manzara
└── Çok kriterli optimizasyon
```

### 4.3 Uzun Vadeli (3-6 ay)

```
Öncelik 1: Graph Neural Network tabanlı kalite tahmini
Öncelik 2: Adaptive routing (kullanıcı profili)
Öncelik 3: Real-time OSM veri güncellemesi
```

---

## 5. Sonuç

Projenin yol bulma algoritmaları genel olarak sağlam bir temel üzerine kurulmuştur. Başlıca güçlü yönler:

1. **Via-Node v3.0:** Endüstri standardı yaklaşım
2. **Multimodal Engine:** Boğaz geçişi korumalı, çok modlu sistem
3. **OSMnx Entegrasyonu:** Güvenilir graf yönetimi

Geliştirilmesi gereken alanlar:

1. **TSP:** Çoklu nokta senaryolarında edge case'ler
2. **Via-Node:** Node attribte doğrulama eksikliği
3. **Penalty System:** Paralel kenar desteği

Sistem, İstanbul için kapsamlı bir yaya ve toplu taşıma yönlendirme çözümü sunmaktadır.

---

**Hazırlayan:** Roo  
**Review:** Önerilen dosyalar: `backend/ALGORITHM_ISSUES.md`, `backend/ALGORITHM_ROADMAP.md`
