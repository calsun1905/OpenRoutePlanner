# Yön Bulma Algoritması Potansiyel Problemler

## Kritik Sorunlar

### 1. TSP: Ulaşılamayan Düğümler (P1 - Orta Öncelik)
**Dosya:** `route_engine_impl.py`  
**Satır:** ~162-169

```python
except nx.NetworkXNoPath:
    dist_matrix[(nodes[i], nodes[j])] = float("inf")
...
w = dist_matrix.get((nodes[i], nodes[j]), float("inf"))
tsp_graph.add_edge(nodes[i], nodes[j], weight=w)
```

**Problem:** Bir düğüme ulaşılamıyorsa sonsuz ağırlık atanıyor ama yine de kenarlık oluşturuluyor. Bu, TSP'nin yanlış sonuç üretmesine veya başarısız olmasına neden olabilir.

**Önerilen Çözüm:** Sonsuz ağırlıklı kenarları ekleme veya yüksek bir threshold kullan.

---

### 2. Via-Node: Node Attribute Eksikliği (P2)
**Dosya:** `route_engine_impl.py`  
**Satır:** ~788-790

```python
for n in main_route_nodes:
    data = G.nodes[n]
    main_coords.append((data.get('y', 0), data.get('x', 0)))
```

**Problem:** Node'larda 'y' veya 'x' attribute yoksa 0 kullanılıyor. Bu, kısa rotalarda bounding box'ın nokta haline gelmesine ve via-node bulunamamasına neden olabilir.

**Önerilen Çözüm:** Attribute yoksa hata fırlat veya minimum bir bounding box oluştur.

---

### 3. Penalty: MultiDiGraph Edge Key Unutulmuş (P2)
**Dosya:** `route_engine_impl.py`  
**Satır:** ~588-593

```python
for edge in used_edges:
    if len(edge) >= 2:
        u, v = edge[0], edge[1]
        edge_key = (min(u, v), max(u, v))
        penalized_edges.add(edge_key)
```

**Problem:** Edge tuple'ındaki key (3. element) ihmal ediliyor. Bu, aynı iki node arasındaki paralel kenarların hepsinin cezalandırılmasına neden olabilir.

**Önerilen Çözüm:** Tüm (u, v, key) kombinasyonlarını izle.

---

### 4. Error Handling: Çok Geniş Exception Yakalama (P3)
**Dosya:** `route_engine_impl.py`  
**Satır:** ~901

```python
except (nx.NetworkXNoPath, Exception):
    continue
```

**Problem:** Tüm Exception'ları yakalamak gerçek bug'ları gizleyebilir. Sadece bilinen hatalar yakalanmalı.

**Önerilen Çözüm:** Sadece `nx.NetworkXNoPath` ve gerekli alt tipleri yakala.

---

### 5. TSP: Aynı Node'a Map Eden Noktalar (P2)
**Dosya:** `route_engine_impl.py`  
**Satır:** ~181

```python
node_to_index = {node: idx for idx, node in enumerate(nodes)}
```

**Problem:** İki farklı koordinat aynı graph node'a map ederse, `node_to_index` sözlüğünde sadece biri kalır. Bu, TSP sonucunun eksik noktalarla dönmesine neden olabilir.

**Önerilen Çözüm:** Her node için sadece bir kez index ekle ve eksik index'leri tamamla.

---

## Düşük Öncelikli Sorunlar

### 6. Fallback: successors/predecessors Kontrolü
**Satır:** ~703-707
MultiDiGraph için successors/predecessors kontrolü doğru görünüyor ama test edilmesi gerekiyor.

### 7. Via-Node: Çok Kısa Rotalarda Bounding Box
Çok kısa rotalarda (örneğin 100m) min_margin sayesinde sorun çözülmüş görünüyor.

### 8. Geometry Extraction: Shapely Hataları
**Satır:** ~81-85
Shapely geometrisi okunamazsa default koordinatlar kullanılıyor - bu kabul edilebilir bir fallback.

---

## Test Önerileri

1. TSP için ulaşılamayan noktalarla test
2. Aynı node'a map eden çoklu noktalarla test
3. MultiDiGraph'ta paralel kenarlarla penalty test
4. Node'larda eksik attribute'lar ile fallback test
