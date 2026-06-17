# Routing Algoritma Analizi Raporu

**Tarih:** 2025-05-25  
**Çalışma Dizini:** C:\Users\batuf\Documents\GitHub\openroute\OpenRoutePlanner  
**Analiz Edilen Dosyalar:**
- `backend/route_engine.py`
- `backend/route_engine_impl.py`
- `backend/graph_manager.py`
- `backend/app.py`

---

## Özet

Toplam **7 olası problem kaynağı** tespit edildi. Bunlardan **2'si kritik (P1/P2)**, **5'i düşük öncelikli (P3)** olarak sınıflandırıldı.

**Debug Logları:** İki kritik problem için debug logları eklendi:
- TSP algoritmasında sonsuz değer ataması için log
- Edge overlap hesaplaması için yönlü/yönsüz karşılaştırma logları

---

## Kritik Problemler (P1/P2)

### 1. TSP Algoritmasında Sonsuz Değer Ataması ⚠️ **P1 - Yüksek**

**Dosya:** [`route_engine_impl.py`](route_engine_impl.py)  
**Fonksiyon:** `solve_tsp()`  
**Satır:** 158-162

**Problem Kodu:**
```python
try:
    length = nx.shortest_path_length(G, nodes[i], nodes[j], weight="length")
    dist_matrix[(nodes[i], nodes[j])] = length
except nx.NetworkXNoPath:
    dist_matrix[(nodes[i], nodes[j])] = float("inf")  # ⚠️ SORUN
```

**Problem Açıklaması:**
NetworkXNoPath durumunda `float("inf")` atanıyor. TSP algoritması (traveling_salesman_problem) sonsuz değerleri düzgün işleyemeyebilir:
- Yanlış sıralama yapabilir
- Bazı noktaları tamamen atlayabilir
- Optimize olmayan rota üretebilir
- Ayrık graf senaryolarında çökme riski

**Etkisi:**
- Çoklu nokta rotalarında yanlış sıralama
- Kullanıcı deneyiminde tutarsızlık
- Bazı noktaların rotadan çıkarılması

**Önerilen Fix:**
```python
except nx.NetworkXNoPath:
    # Sonsuz yerine çok büyük ama sonlu bir değer kullan
    dist_matrix[(nodes[i], nodes[j])] = 999999.0
    # VEYA: O nokta çiftini TSP matrisinden çıkar
    # VEYA: Fallback rota stratejisi uygula
```

**Debug Log (Eklendi):**
```python
no_path_count += 1
no_path_pairs.append((nodes[i], nodes[j]))
print(f"[TSP DEBUG] NetworkXNoPath: node {nodes[i]} -> {nodes[j]} (inf atandı)")

if no_path_count > 0:
    print(f"[TSP DEBUG] ⚠️  {no_path_count} çift için yol bulunamadı (inf atandı)")
```

---

### 2. Asimetrik Edge Overlap Hesaplaması ⚠️ **P2 - Orta**

**Dosya:** [`route_engine_impl.py`](route_engine_impl.py)  
**Fonksiyon:** `count_edge_overlap()`  
**Satır:** 313-316

**Problem Kodu:**
```python
def normalize_edge(edge):
    if len(edge) >= 2:
        u, v = edge[0], edge[1]
        return (min(u, v), max(u, v))  # ⚠️ Yönsuz çift
    return edge
```

**Problem Açıklaması:**
Yürüme rotalarında yön önemli olabilir. (u,v) ve (v,u) farklı sokaklar olabilir. Yönsuz normalization:
- Yanlış overlap sonuçları üretebilir
- Alternatif rotaların gerçekten farklı olup olmadığını yanlış değerlendirebilir
- Aynı sokakta ters yöne giden rotaları aynı kabul edebilir

**Örnek Senaryo:**
```python
# Rota 1: 1 -> 2 -> 3 (doğru yön)
edges1 = [(1, 2, 0), (2, 3, 0)]

# Rota 2: 3 -> 2 -> 1 (ters yön)
edges2 = [(3, 2, 0), (2, 1, 0)]

# Mevcut kod: %100 overlap (yanlış!)
# Gerçek: %0 overlap (farklı yönler)
```

**Etkisi:**
- Alternatif rotaların reddedilmesi
- Kullanıcıya benzer rotalar sunulması
- Alternatif rota üretiminin başarısız olması

**Önerilen Fix:**
```python
# Yönlü edge comparison kullan
def normalize_edge(edge):
    if len(edge) >= 2:
        u, v = edge[0], edge[1]
        return (u, v)  # Yönlü çift
    return edge
```

**Debug Log (Eklendi):**
```python
directional_set1 = {(e[0], e[1]) for e in edges1 if len(e) >= 2}
directional_set2 = {(e[0], e[1]) for e in edges2 if len(e) >= 2}
directional_intersection = len(directional_set1 & directional_set2)

print(f"[OVERLAP DEBUG] Yönsuz overlap: {intersection}/{len(set2)} = {intersection/len(set2):.2%}")
print(f"[OVERLAP DEBUG] Yönlü overlap: {directional_intersection}/{len(directional_set2)} = {directional_intersection/len(directional_set2):.2%}")

if intersection != directional_intersection:
    print(f"[OVERLAP DEBUG] ⚠️  Yönlü ve yönsuz overlap farkı: {abs(intersection - directional_intersection)} edge")
```

---

## Düşük Öncelikli Problemler (P3)

### 3. Penalty-Based Generation'da Gövde-Only Yaklaşımı ℹ️ **P3 - Düşük**

**Dosya:** [`route_engine_impl.py`](route_engine_impl.py)  
**Fonksiyon:** `get_body_edges()`  
**Satır:** 748-758

**Problem Kodu:**
```python
def get_body_edges(edges, skip_ratio=0.10):
    n = len(edges)
    if n <= 4:
        return edges
    skip = max(1, int(n * skip_ratio))
    return edges[skip:-skip]  # Baş/son %10 atlanıyor
```

**Problem Açıklaması:**
Baş/son %10 atlanıyor, bu zikzak rotalarını engellemek için tasarlanmış ama başlangıç/bitiş varyasyonunu kısıtlayabilir.

**Etkisi:**
- Alternatif rotaların başlangıç/bitiş noktalarında varyasyon azalması
- Kısa rotalarda tüm kenarların cezalandırılması

**Önerilen Fix:**
- Dinamik skip_ratio kullan (rota uzunluğuna göre)
- Veya minimum edge sayısı kontrolü ekle

---

### 4. Via-Node Seçiminde Sabit Sample Count ℹ️ **P3 - Düşük**

**Dosya:** [`route_engine_impl.py`](route_engine_impl.py)  
**Fonksiyon:** `find_via_node_routes()`  
**Satır:** 832-833

**Problem Kodu:**
```python
sample_count = ROUTE_CONFIG.get("VIA_NODE_ROUTE_SAMPLE_COUNT", 20)
sampled_coords = main_coords[::max(1, len(main_coords) // sample_count)]
```

**Problem Açıklaması:**
sample_count sabit 20, çok uzun rotalarda yetersiz olabilir.

**Etkisi:**
- Uzun rotalarda via-node seçiminin doğruluğu azalması
- Performans sorunu (çok fazla nokta işlenmesi)

**Önerilen Fix:**
- Dinamik sample_count kullan (rota uzunluğuna göre)
- Veya maksimum sample limiti ekle

---

### 5. Coordinate Precision Toleransı ℹ️ **P3 - Düşük**

**Dosya:** [`app.py`](app.py)  
**Fonksiyon:** `_coords_equal()`  
**Satır:** 1312-1318

**Problem Kodu:**
```python
def _coords_equal(a, b):
    if len(a) != len(b):
        return False
    for i in range(len(a)):
        if abs(a[i][0] - b[i][0]) > 1e-6 or abs(a[i][1] - b[i][1]) > 1e-6:  # ⚠️ Sabit tolerans
            return False
    return True
```

**Problem Açıklaması:**
1e-6 toleransı, çok uzun rotalarda yetersiz kalabilir.

**Etkisi:**
- Uzun rotalarda yanlış karşılaştırma
- Aynı rotaların farklı kabul edilmesi

**Önerilen Fix:**
- Dinamik tolerans kullan (rota uzunluğuna göre)
- Veya mesafe tabanlı karşılaştırma

---

### 6. Nearest Edge Snap Distance Kontrolü ℹ️ **P3 - Düşük**

**Dosya:** [`app.py`](app.py)  
**Fonksiyon:** `_validate_route_snaps()`  
**Satır:** 131-154

**Problem Kodu:**
```python
max_snap_m = float(ROUTE_CONFIG.get("ROUTE_SNAP_MAX_DISTANCE_M", 750))
if snap_m > max_snap_m:
    return False, {
        "error": "Secilen nokta yurunebilir yol agina cok uzak.",
        "code": "snap_too_far",
        ...
    }
```

**Problem Açıklaması:**
max_snap_m kontrolü var ama fallback stratejisi yetersiz olabilir.

**Etkisi:**
- Kullanıcıya hata mesajı verilmesi
- Alternatif rota seçeneği sunulmaması

**Önerilen Fix:**
- Fallback stratejisi ekle (daha geniş graf denemesi)
- Veya kullanıcıya öneri sun

---

### 7. MultiDiGraph'ta Edge Direction Kontrolü ℹ️ **P3 - Düşük**

**Dosya:** [`route_engine_impl.py`](route_engine_impl.py)  
**Fonksiyon:** `_is_valid_path()`  
**Satır:** 60-64

**Problem Kodu:**
```python
def _is_valid_path(G, path_nodes: list) -> bool:
    """Check that every consecutive node pair is connected in route direction."""
    if not path_nodes:
        return False
    return all(G.has_edge(path_nodes[i], path_nodes[i + 1]) for i in range(len(path_nodes) - 1))
```

**Problem Açıklaması:**
Sadece `G.has_edge()` kontrolü var, direction kontrolü eksik.

**Etkisi:**
- Ters yöne giden rotaların kabul edilmesi
- Yürüme rotalarında hatalı yön

**Önerilen Fix:**
- MultiDiGraph için direction kontrolü ekle
- Veya edge data kontrolü

---

## Debug Log Özeti

Eklenen debug logları:

### TSP Debug Logları
- NetworkXNoPath oluşan çift sayısı
- Hangi node çiftleri için yol bulunamadı
- Sonsuz değer atanan çiftler

### Edge Overlap Debug Logları
- Yönsuz overlap değeri
- Yönlü overlap değeri
- İki değer arasındaki fark

Bu loglar çalışma zamanında görüntülenebilir ve problemlerin doğrulanmasına yardımcı olur.

---

## Test Önerileri

1. **TSP Testi:** Ayrık graf senaryosu oluştur (node'lar arası yol yok)
2. **Edge Overlap Testi:** Aynı sokakta ters yöne giden rotaları test et
3. **Via-Node Testi:** Çok uzun rota (100+ node) ile test et
4. **Coordinate Precision Testi:** Uzun rota (10+ km) ile test et

---

## Sonuç

Toplam **7 problem** tespit edildi:
- **2 kritik (P1/P2):** TSP sonsuz değeri, Edge overlap yönsüz normalization
- **5 düşük öncelikli (P3):** Gövde-only penalty, Via-node sample count, Coordinate precision, Snap distance, Edge direction

**Debug logları eklendi** ve çalışma zamanında görüntülenebilir.

**Öncelikli Fix:** TSP algoritmasındaki sonsuz değer ataması ve Edge overlap yönlü normalization.