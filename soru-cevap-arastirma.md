# OpenRoutePlanner Proje Soru-Cevap Arştırması

Bu dosya proje mimarisi ve kod yapısı hakkında yapılan soru-cevap oturumunu içerir.

---

## Soru 1: Rota Bulma Algoritmaları Kodda Hangi Algoritmalar Nerede Kullanılıyor?

### Cevap:
Kodunuzda **5 ana algoritma** kullanılıyor:

| Algoritma | Fonksiyon | Dosya Satırı | Ne İşe Yarar? |
|-----------|-----------|--------------|---------------|
| **Dijkstra** | `shortest_path()` | route_engine_impl.py:76-96 | En kısa yolu bulur (temel rota) |
| **TSP** | `solve_tsp()` | route_engine_impl.py:187-296 | Çoklu nokta için en verimli sırayı bulur |
| **Via-Node** | `find_via_node_routes()` | route_engine_impl.py:885-1036 | Alternatif rotalar için ara kavşaklar bulur |
| **Edge Disjoint Paths** | `find_disjoint_paths()` | route_engine_impl.py:557-610 | Birbirini kesmeyen yollar bulur |
| **Penalty-based** | `find_routes_with_penalty()` | route_engine_impl.py:715-777 | Kullanılan yollara ceza vererek yeni rotalar bulur |

**Kullanım Sırası:**
1. **Rota 1** → Dijkstra (en kısa)
2. **Rota 2-3** → Via-Node (ana yöntem)
3. **Yedek** → Penalty (via-node yetmezse)

---

## Soru 2: Rota Bulma Algoritmalarının Birbirlerine Farkları Nelerdir?

### Cevap:

| Algoritma | Temel Fark | Avantajı | Dezavantajı | Kullanım Amacı |
|-----------|------------|----------|-------------|----------------|
| **Dijkstra** | En kısa mesafeyi bulur | Garantili en kısa yol | Sadece 1 rota | Ana rota (Rota 1) |
| **TSP** | Noktaları optimize eder | Çoklu durak için en verimli sıra | Hesaplama maliyeti yüksek | 3+ nokta inputu |
| **Via-Node** | Ana rotadan **uzak** kavşaklara götürür | Gerçekten farklı güzergahlar | Çok uzun rotalar üretebilir | Alternatif rotalar (Rota 2-3) |
| **Edge Disjoint** | Yollar **kesişmez** | Tamamen ayrı yollar | OSM çıkmaz sokak problemi | Topoloji analizi |
| **Penalty** | Kullanılan yollar **pahalılaşır** | Basit ve güvenilir | Zikzak yapabilir | Yedek strateji |

**En Kritik Fark:**

```
Via-Node: "Ana rotadan uzak kavşak bul → Oradan geçir" (Google Maps tarzı)
Penalty: "Kullanılan yolları cezala → Dijkstra tekrar çalıştır"
```

Via-Node daha **doğal** alternatifler üretir, Penalty ise **yedek** olarak kullanılır.

---

## Soru 3: Pruning Mekanizması Kodda Var Mı ve Ne İşe Yarıyor?

### Cevap:

**Evet, kodda pruning (budeme) mekanizması var.** Birkaç farklı yerde kullanılıyor:

| Pruning Türü | Kod Yeri | Ne İşe Yarıyor? |
|--------------|----------|-----------------|
| **Via-Node Aday Sınırı** | route_engine_impl.py:988 | `MAX_CANDIDATES=30` → En fazla 30 kavşak dener |
| **Uzunluk Pruning** | route_engine_impl.py:1001-1003 | `max_distance_ratio=1.5` → Ana rotadan 1.5x uzun olanlar reddedilir |
| **Overlap Pruning** | route_engine_impl.py:1009-1016 | Kendisiyle %70+ örtüşen rotalar reddedilir |
| **Edge Disjoint Cutoff** | route_engine_impl.py:581 | `cutoff=num_routes` → Disjoint path aramayı sınırlar |

**Örnek Kod:**
```python
# Çok uzun rota reddedilir (pruning)
if stats["total_distance_km"] > max_km:  # max_km = main_km * 1.5
    continue  # Budeme: bu rota atılır
```

**Neden Gerekli?**
- **Performans:** Binlerce adayı denemek yerine en iyileri seçer
- **Kalite:** Çok uzun veya çok benzer rotaları kullanıcıya sunmaz

---

## Soru 4: Proje Frontend Olarak Neden Leaflet Üzerine Kurulmuştur?

### Cevap:

**Frontend'de Leaflet kullanılıyor.** Nedenleri:

| Sebep | Açıklama |
|--------|----------|
| **Açık Kaynak** | Ücretsiz, ticari kullanım izni var |
| **OSM Uyumlu** | OpenStreetMap ile mükemmel çalışır |
| **Build Yok** | Vanilla JS → npm/webpack gerektirmez |
| **Hafif** | ~140KB (Mapbox ~400KB+) |
| **Plugin Zengin** | MarkerCluster, Routing, Heatmap vb. |
| **Mobil Dostu** | Touch events önceden tanımlı |
| **Kolay API** | Basit syntax: `L.map('map').setView()` |

**Proje İçin Spesifik Neden:**
- Backend Python (Flask) olduğu için frontend vanilla JS
- Build step istenmemiyor (sadece HTML + JS)
- OSM verisi kullanıldığı için doğal pairing

**Alternatifler Neden Değil?**
- **Google Maps:** API key gerektirir, ücretli
- **Mapbox:** Ücretli, build step gerekir
- **OpenLayers:** Daha karmaşık API

**Kod Referansı:**
- HTML: [index.html:11-14](frontend/index.html#L11-L14) - Leaflet CSS import
- HTML: [index.html:653-654](frontend/index.html#L653-L654) - Leaflet JS import

---

## Soru 5: OpenStreetMap'ten Alınan Harita Tam Olarak Nerede ve Kodun Hangi Parçasında Nasıl Entegre Ediliyor Uygulamamıza?

### Cevap:

**Harita 2 katmanlı entegre edilmiş:**

### 🔷 Frontend (Görsel Harita)
| Konum | Kod | Ne İşe Yarar? |
|-------|-----|---------------|
| Tile Layer | [app.js:106-109](frontend/js/app.js#L106-L109) | OSM tile'larını çeker (görsel) |
| Harita Başlatma | [app.js:98-100](frontend/js/app.js#L98-L100) | İstanbul merkez: `L.map("map")` |

**Kod:**
```javascript
// Tile Layer - OSM tiles
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
}).addTo(map);
```

### 🔶 Backend (Rota Grafiği)
| Fonksiyon | Satır | Ne İşe Yarar? |
|-----------|------|---------------|
| `get_graph()` | [graph_manager.py:339](backend/graph_manager.py#L339) | İsim ile graph indirir |
| `get_graph_for_points()` | [graph_manager.py:370](backend/graph_manager.py#L370) | Koordinat ile graph indirir |
| `ox.graph_from_place()` | 353. satır | OSM'den yer ismi ile indir |
| `ox.graph_from_point()` | 456. satır | OSM'den koordinat ile indir |

**Kod:**
```python
# Backend - OSMnx ile graph indirme
G = ox.graph_from_point(
    (center_lat, center_lon),
    dist=radius,  # metre cinsinden
    network_type="walk",
)
ox.save_graphml(G, cache_file)  # Disk'e cache'ler
```

### 🔄 Veri Akışı
```
1. Frontend: Kullanıcı haritaya tıklar → (lat, lon)
2. Backend: get_graph_for_points(points) çağrılır
3. OSMnx: OpenStreetMap'ten graph indirir
4. Cache: .graphml dosyasına kaydedilir
5. Route Engine: Dijkstra ile rota hesaplar
6. Frontend: Rota polyline olarak çizilir
```

---

## Soru 6: RAG Yaparken Hangi Yöntem Kullanılmıştır?

### Cevap:

**Evet, projede RAG kullanılıyor.** İki farklı sistem var:

### 🔹 RAG Service (LLM Bağlam İçin)
| Özellik | Değer |
|---------|-------|
| **Vector DB** | ChromaDB (PersistentClient) |
| **Embedding Model** | `BAAI/bge-m3` (sentence-transformers) |
| **Collection** | `istanbul_rag_core` |
| **Dosya** | [services/rag_service.py](backend/services/rag_service.py) |

**Kod Referansı:**
```python
# rag_service.py:134-150
def rag_query(question: str, *, top_k: int = 5):
    embedder = SentenceTransformer(_embed_model_name())  # BAAI/bge-m3
    q_emb = embedder.encode([user_q], normalize_embeddings=True).tolist()
    res = col.query(query_embeddings=q_emb, n_results=k)
```

### 🔹 BERT NLP Engine (Türkçe Parsing İçin)
| Özellik | Değer |
|---------|-------|
| **Model** | `dbmdz/bert-base-turkish-uncased` |
| **Amaç** | Türkçe sorgu parsing (Kadıköy'den Taksim'e...) |
| **Dosya** | [nlp/bert_nlp_engine.py](backend/nlp/bert_nlp_engine.py) |

**Fark:**
- **RAG:** LLM prompt'una bağlam ekler (proje dökümanları, README vb.)
- **BERT NLP:** Türkçe sorguları parse eder (yer isimleri çıkarır)

---

## Soru 7: Flask API Olduğu Yazıyor Kodda Business Logic ile İlgili Bu Flask API Nedir Tam Olarak?

### Cevap:

**Flask API, Frontend ile Backend arasındaki köprüdür.**

### 🏪 Basit Bir Örnek - Market

```
MÜŞTERİ (Frontend) ──→ KASIYER (Flask API) ──→ DEPO (Business Logic)
     "5 kg elma"           Siparişi al             Rafları kontrol et
                           Fiyat hesapla            Ürünü getir
                           Ödeme al                 Stok düş
                           Fiş yazdır                Fiş ver
```

### 📱 OpenRoutePlanner'da Aynı Mantık

```
KULLANICI (Tarayıcı) ──→ FLASK API ──→ ROTA MOTORU (Business Logic)
  "Kadıköy'den           İsteği al            Graph'ı indir
   Taksim'a rota"        Koordinatları         Dijkstra çalıştır
                        kontrol et            Mesafeyi hesapla
                        JSON hazırla          Rotayı çiz
                        Cevap gönder          Sonucu ver
```

### 🔧 Flask API Ne Yapıyor?

**Sadece ARACI görevi:**

1. **İstek Alır:** "Kullanıcı 3 nokta seçti"
2. **Kontrol Eder:** "Koordinatlar geçerli mi? İstanbul içinde mi?"
3. **Emre Gider:** "Ey route_engine, şu noktalar için rota hesapla"
4. **Sonucu Alır:** Route motorundan rota verisi gelir
5. **Paketler:** JSON formatına çevirir
6. **Gönderir:** Tarayıcıya cevabı yollar

### 🎭 En Özet Hali

| Katman | Görev | Benzetme |
|--------|-------|----------|
| **Flask API** | Kurye | Siparişi alıp, depodan ürünü getirip fiş yazdırır |
| **Business Logic** | Depo | Rafları yönetir, ürünü hazırlar |
| **Data Layer** | Tedarikçi | Ürünleri (graph verisi) sağlar |

### 💡 Neden Ayrı?

- **Flask API:** HTTP konuşur (tarayıcı ile anlaşır)
- **Business Logic:** Matematik hesaplar (Dijkstra, TSP)
- **Ayrım Gerekli:** Route motoru Python ama tarayıcı JavaScript - Flask translator gibi çalışır

### 📋 Flask API'ın Ana Görevleri

| Görev | Açıklama | Örnek |
|-------|----------|-------|
| **Validasyon** | Girdileri kontrol eder | "Koordinatlar geçerli mi?" |
| **Geofence** | İstanbul sınırları kontrolü | "Bu nokta İstanbul'da mı?" |
| **Koordinatör** | Business logic'i çağırır | "Route_engine, çalış!" |
| **Response** | JSON cevap döner | `{"route_coords": [...]}` |

### 📁 Kullanılan Endpoint'ler

| Endpoint | İşlev |
|----------|-------|
| `/api/get-route` | Ana rota hesaplar |
| `/api/get-alternative-routes` | 3 alternatif rota |
| `/api/search-pois` | POI arama |
| `/api/geocode` | Adres → koordinat |
| `/api/routes/save` | Rota kaydetme |

### 🎯 İş Bölümü

| Katman | Sorumlu | Dosya |
|--------|---------|-------|
| **Flask API** | HTTP, validasyon, JSON | [app.py](backend/app.py) |
| **Business Logic** | Rota algoritmaları | [route_engine_impl.py](backend/route_engine_impl.py) |
| **Data Layer** | Graph yönetimi | [graph_manager.py](backend/graph_manager.py) |

---

**Önemli Not:** Bu dosya soru-cevap oturumu sırasında oluşturulmuştur. Tüm 7 sorunun cevabı eklenmiştir.

**Özet:**
1. ✅ Rota algoritmaları: Dijkstra, TSP, Via-Node, Edge Disjoint, Penalty
2. ✅ Algoritma farkları: Kullanım amaçları ve avantaj/dezavantajları
3. ✅ Pruning mekanizması: Via-node aday sınırı, uzunluk, overlap pruning
4. ✅ Leaflet neden seçildi: OSM uyumu, build yok, hafif
5. ✅ OSM entegrasyonu: Frontend tile layer + Backend OSMnx graph
6. ✅ RAG yöntemi: ChromaDB + BAAI/bge-m3 embedding
7. ✅ Flask API: HTTP köpüsü, validasyon, business logic coordinatörü
