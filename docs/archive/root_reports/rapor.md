# OpenRoutePlanner — Bitirme Projesi Raporu

**Proje Adı:** OpenRoutePlanner  
**Konu:** Türkiye için Yapay Zeka Destekli Rota Planlama Uygulaması  
**Tarih:** Nisan 2026

---

## 1. Giriş

OpenRoutePlanner, İstanbul ve Türkiye genelinde çalışan, yapay zeka destekli bir rota planlama web uygulamasıdır. Kullanıcılar harita üzerinde noktalar seçerek veya doğal dilde Türkçe sorgular yazarak rota oluşturabilir, alternatif güzergahlar arasından seçim yapabilir ve toplu taşıma ile yürüyüş seçeneklerini karşılaştırabilir.

Proje, graf teorisi algoritmalarından doğal dil işleme (NLP) tekniklerine, mekansal indekslemeden hava durumu entegrasyonuna kadar geniş bir teknik yelpazede çalışmaktadır.

---

## 2. Sistem Mimarisi

### 2.1 Genel Mimari

Uygulama **istemci-sunucu (client-server)** mimarisine sahiptir:

| Katman | Teknoloji | Açıklama |
|--------|-----------|----------|
| **Frontend** | HTML, CSS, JavaScript, Leaflet.js | Harita arayüzü ve kullanıcı etkileşimi |
| **Backend** | Python, Flask | REST API sunucusu |
| **Veritabanı** | SQLite | Uygulama verileri ve cache |
| **Harita Verisi** | OpenStreetMap (OSMnx) | Sokak ağı graf verileri |
| **NLP Modeli** | BERT (PyTorch, Transformers) | Doğal dil anlama |
| **Toplu Taşıma** | İBB SOAP API, Metro Istanbul API | Otobüs/metro verileri |
| **Hava Durumu** | Open-Meteo API | Anlık ve saatlik tahmin |
| **LLM Sohbet** | Google Gemini / OpenRouter | Yapay zeka sohbet asistanı |

### 2.2 Backend Modül Yapısı

```
backend/
├── app.py                  # Flask ana uygulama, API endpoint'leri
├── route_engine_impl.py    # Rota hesaplama çekirdeği (Dijkstra, TSP, Alternatif)
├── graph_manager.py        # OSMnx graf yönetimi ve cache
├── bert_engine.py          # BERT model yükleme ve embedding
├── bert_nlp_engine.py      # BERT tabanlı NLP sistemi
├── nlp_concept_resolver.py # POI konsept çözümleyici
├── multimodal_engine.py    # Yürüyüş + toplu taşıma karşılaştırma
├── ibb_transit.py          # İBB otobüs/metro veri modülü
├── geocoder.py             # Nominatim geocoding + cache
├── weather_service.py      # Open-Meteo hava durumu servisi
├── spatial_index.py        # Grid tabanlı mekansal indeksleme
├── time_planner.py         # Zaman çizelgesi ve çakışma kontrolü
├── gemini_service.py       # Google Gemini LLM entegrasyonu
├── openrouter_service.py   # OpenRouter LLM entegrasyonu
├── route_storage.py        # Rota CRUD (SQLite)
├── location_storage.py     # Konum CRUD (SQLite)
└── storage_db.py           # SQLite veritabanı yardımcıları
```

---

## 3. Kullanılan Algoritmalar

### 3.1 Dijkstra'nın En Kısa Yol Algoritması

**Amaç:** İki nokta (sokak kavşağı) arasındaki en kısa mesafeli yolu bulmak.

**Matematiksel Temel:**

Verilen ağırlıklı graf G = (V, E) ve başlangıç düğümü s için:

```
d(s) = 0
d(v) = ∞  (tüm diğer v ∈ V için)

Her adımda:
  u = argmin{d(v) : v ∈ Q}     ← Minimum mesafeli düğümü seç
  Her komşu v için:
    if d(u) + w(u,v) < d(v):
      d(v) = d(u) + w(u,v)     ← Relax işlemi
```

**Projede Kullanımı:**

```python
path = nx.shortest_path(G, origin_node, dest_node, weight="length")
```

- `weight="length"` → kenar ağırlığı metre cinsinden yol uzunluğu
- NetworkX binary heap tabanlı priority queue kullanır
- 3 farklı yerde çağrılır: doğrudan rota, TSP mesafe matrisi ve alternatif rota fallback

**Karmaşıklık:** O((V + E) · log V), burada V ≈ 10.000–50.000 kavşak, E ≈ 15.000–80.000 sokak segmenti

---

### 3.2 TSP Approximation (Gezgin Satıcı Problemi)

**Amaç:** N noktanın en verimli ziyaret sırasını bulmak (toplam mesafeyi minimize etmek).

**Problem:** TSP NP-hard bir problemdir. N nokta için olası permütasyon sayısı (n-1)!/2'dir. Optimal çözüm büyük N değerlerinde pratikte hesaplanamaz, bu nedenle yaklaşım algoritması kullanılır.

**Projede Kullanılan Yaklaşım (Christofides):**

1. Her nokta `find_nearest_node()` ile en yakın graf düğümüne eşlenir
2. Her düğüm çifti arası Dijkstra ile mesafe hesaplanır → **n²** Dijkstra çağrısı
3. Tam bağlantılı (complete) graf oluşturulur
4. `traveling_salesman_problem(graph, cycle=False)` çağrılır

NetworkX'in iç algoritması:
1. Minimum Spanning Tree (MST) oluşturur
2. Tek dereceli düğümleri bulur
3. Minimum ağırlıklı tam eşleme yapar
4. MST + eşleme = Euler Grafı → Euler turu bulur
5. Tekrarlayan düğümleri atlayarak Hamilton yolu oluşturur

**Garanti:** Optimal çözümün en fazla **1.5 katı** kadar uzun.

**Karmaşıklık:** O(n² · (V+E) log V)

---

### 3.3 Via-Node Alternatif Rota Üretimi

**Amaç:** İki nokta arası birden fazla farklı güzergah oluşturmak (Google Maps / OSRM tarzı).

**Algoritma:**

1. Ana rota hesaplanır (Dijkstra)
2. Ana rota koordinatlarının bounding box'ı genişletilir (%30)
3. Bounding box içindeki yüksek dereceli (kavşak) düğümler bulunur
4. Ana rotadan geometrik olarak en uzak olanlar via-node olarak seçilir
5. A → via-node → B rotası oluşturulur
6. Çok uzun rotalar reddedilir (`max_distance_ratio` kontrolü)

**Destekleyici Mekanizmalar:**

- **Asimetrik Edge Overlap:** Yeni rotanın kenarlarının ne kadarının eski rotayla örtüştüğünü ölçer. Jaccard yerine asimetrik formül kullanılır çünkü Jaccard alt küme durumunu yakalayamaz.
- **Gövde-Only Penalty:** Baş ve son %10'luk kısma dokunmadan sadece gövde kenarlarına ceza uygulayarak zikzak oluşmasını önler.
- **Dinamik Overlap Eşiği:** Rota uzunluğuna göre kabul edilen benzerlik oranı değişir (kısa rotalar: %90, uzun rotalar: %70).
- **Edge Connectivity (Menger Teoremi):** Topoloji ön-analizi ile maksimum farklı yol sayısı önceden tahmin edilir.

---

### 3.4 Haversine Mesafe Formülü

**Amaç:** İki GPS koordinatı arasındaki küresel (great-circle) mesafeyi hesaplamak.

**Formül:**

```
a = sin²(Δφ/2) + cos(φ₁) · cos(φ₂) · sin²(Δλ/2)
c = 2 · arcsin(√a)
d = R · c

R = 6.371.000 m (Dünya yarıçapı)
φ = enlem (radyan), λ = boylam (radyan)
```

**Kullanım Alanları:**
- Graf indirme yarıçapı hesabı
- Durak yakınlık sorguları
- Yürüme mesafesi tahmini
- Toplu taşıma durak eşleştirme

---

### 3.5 R-tree / Grid Tabanlı Mekansal İndeksleme

**Amaç:** Koordinat bazlı hızlı arama ve en yakın nokta bulma.

**Projede İki Seviyede Kullanılır:**

1. **OSMnx R-tree (Nearest Edge):** Kullanıcının tıkladığı koordinatı en yakın sokak segmentine snap eder. `ox.nearest_edges()` fonksiyonu R-tree yapısı ile O(log n) karmaşıklıkta çalışır.

2. **Grid Tabanlı SpatialIndex (POI Cache):** POI aramaları için özel implementasyon. Koordinat düzlemini grid hücrelerine böler (~1 km), her hücrede POI listesi tutar. Bounding box ve yarıçap sorguları destekler.

```python
class SpatialIndex:
    def _get_cell_key(self, lon, lat):
        return (int(lon / self.grid_size), int(lat / self.grid_size))
```

---

### 3.6 Cosine Similarity (Kosinüs Benzerliği)

**Amaç:** İki vektör arasındaki açısal benzerliği ölçmek.

**Formül:**

```
cos(θ) = (a · b) / (‖a‖ · ‖b‖)
```

- 1.0 = aynı yön (aynı anlam)
- 0.0 = dik (ilişkisiz)

**Projede Vektörize Hesaplama:**

```python
similarities = np.dot(embeddings, query_embedding)
norms = np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
similarities = similarities / norms
```

NumPy ile tüm yer isimleriyle tek seferde hesaplanır → O(n · d), d=768.

---

## 4. Yapay Zeka ve Doğal Dil İşleme (NLP)

### 4.1 BERT Modeli

**Model:** `dbmdz/bert-base-turkish-uncased`

| Özellik | Değer |
|---------|-------|
| Parametre sayısı | ~110 milyon |
| Embedding boyutu | 768 |
| Maksimum token | 128 |
| Disk boyutu | ~440 MB |
| Eğitim verisi | Türkçe Wikipedia + web corpus |

**BERT Encoding Süreci:**

1. **WordPiece Tokenization:** Metni alt-kelime parçalarına ayırır
   - Örnek: "Kadıköy'den" → `["kad", "##ıköy", "##'den"]`
2. **Self-Attention:** Her token diğer tüm tokenlarla ilişkisini hesaplar (12 Transformer katmanı)
3. **[CLS] Token:** Tüm cümlenin anlamını temsil eden 768 boyutlu özet vektör

### 4.2 Sorgu Tipi Sınıflandırma (Semantic Search)

Kullanıcı sorgusu, önceden tanımlı template cümlelerin embedding'leriyle karşılaştırılır:

| Tip | Örnek Template |
|-----|----------------|
| `route` | "Kadıköy'den Beşiktaş'a rota" |
| `poi` | "Kadıköy'de neler var" |
| `multi` | "Kadıköy, Taksim ve Beşiktaş'ı gez" |
| `single` | "Taksim'e git" |

**Intent Conflict Matrix:** Yapısal sinyaller (yön eki, yer sayısı, POI konsepti) ile BERT skoru arasındaki çatışmalar deterministik kurallarla çözülür.

**Hard-Negative Filtering:** "Merhaba", "saat kaç" gibi rota ile ilgisiz sorgular tespit edilerek `unknown` olarak sınıflandırılır.

### 4.3 Yer İsmi Çıkarımı (NER)

**N-gram Tabanlı Yaklaşım:**

1. Sorgudan 1-gram, 2-gram ve 3-gram aday span'ler çıkarılır
2. Türkçe ek soyma (suffix stripping) uygulanır
3. Her span BERT embedding'i ile yer veritabanındaki isimlerin embedding'leriyle karşılaştırılır
4. Eşik değerler: tek kelime → 0.75, çok kelime → 0.65

**Türkçe Rol İpucu Sistemi:**

```python
# "Kadıköy'den" → ("kadıköy", "from")
# "Taksim'e"    → ("taksim", "to")
# "Beşiktaş'ta" → ("beşiktaş", "loc")
```

Ayrılma (ablative), yönelme (dative) ve bulunma (locative) hal ekleri otomatik algılanarak başlangıç/hedef/konum rolleri belirlenir.

### 4.4 POI Konsept Çözümleyici

Türkçe morfolojik analiz ile POI kategorisi çözülür:

1. **Morfolojik Adaylar:** "eczanelerden" → ["eczanelerden", "eczaneler", "eczane"]
2. **Sözlük Doğrulama:** Aday → OSM POI eşleştirme sözlüğünde arama
3. **Yakın String Eşleştirme:** `difflib.get_close_matches` ile %90 benzerlik eşiği
4. **BERT Fallback:** Sözlükte bulunamazsa semantik benzerlik

17 POI kategorisi desteklenir: restoran, kafe, ATM, eczane, market, hastane, cami vb.

### 4.5 LLM Sohbet Entegrasyonu

İki farklı LLM sağlayıcısı entegre edilmiştir:

- **Google Gemini:** Generative Language API ile doğrudan entegrasyon
- **OpenRouter:** Çoklu model desteği ile fallback mekanizması

Her iki servis de model fallback zinciri, streaming yanıt ve hata yönetimi sunar.

---

## 5. Toplu Taşıma Entegrasyonu (Multimodal)

### 5.1 Veri Kaynakları

| Kaynak | API | Veri |
|--------|-----|------|
| İETT | SOAP XML API | Otobüs durakları, hatlar, güzergahlar |
| Metro İstanbul | REST JSON API | Metro/tramvay/füniküler istasyonları |
| OSRM | HTTP API | Yol bazlı routing (driving/foot) |

### 5.2 Multimodal Rota Algoritması

1. Başlangıç ve hedef noktalar etrafında yakın duraklar aranır (Haversine + bounding box)
2. Ortak hatlar SQLite JOIN ile bulunur
3. Yürüyüş + otobüs/metro + yürüyüş segmentleri oluşturulur
4. Her segment için süre hesaplanır (yürüyüş: 5 km/s, otobüs: 18 km/s, metro: 34 km/s)
5. Direkt yürüyüş ile toplu taşıma karşılaştırılır
6. Transferli rotalar için multi-hat graph traversal uygulanır

### 5.3 İstanbul'a Özel Kısıtlamalar

- **Boğaz Geçişi:** İki yaka arası yürüyüş fiilen mümkün değildir, bu rotalar otomatik reddedilir
- **Haliç Geçişi:** Köprü checkpoint'leri ile OSRM koordinatlarının gerçek yol takip edip etmediği doğrulanır
- **Vapur Hatları:** Üsküdar-Kabataş, Kadıköy-Eminönü gibi bilinen vapur bağlantıları

---

## 6. Veri Yönetimi ve Cache

### 6.1 Geocoding (Yer İsmi ↔ Koordinat)

**Çift Katmanlı Cache Mimarisi:**

```
Sorgu → Memory Cache? → Hit → Döndür
                      → Miss → SQLite Cache? → Hit → Memory'ye yaz + Döndür
                                              → Miss → Rate Limit (1s) → Nominatim API → Her ikisine kaydet
```

**MD5 Hashing:** Sorgu stringi → 32 karakterlik benzersiz hash → SQLite primary key

**Rate Limiting:** Nominatim kullanım şartı gereği maksimum 1 istek/saniye.

### 6.2 Graf Cache

| Yöntem | Key Format | Süre |
|--------|------------|------|
| Bölge adı | `kadikoy_istanbul_turkey.graphml` | Kalıcı (disk) |
| Koordinat | `point_40.9903_29.0291_800.graphml` | Kalıcı (disk) |
| Memory | Python dict | Uygulama ömrü |

OSMnx ile OpenStreetMap'ten indirilen sokak ağları **MultiDiGraph** (yönlü, çoklu kenar destekli graf) olarak `.graphml` formatında saklanır.

### 6.3 Hava Durumu Cache

- **Sağlayıcı:** Open-Meteo API
- **Cache TTL:** 900 saniye (15 dakika)
- **Retry:** Exponential backoff ile 3 deneme
- **Özellikler:** Anlık hava, saatlik forecast, rota boyunca hava kontrolü

---

## 7. Zaman Planlama

### 7.1 Timeline Oluşturma

Rota üzerindeki her durak için sıralı zaman çizelgesi oluşturulur:

```
süre_dakika = (mesafe_km / hız_km_saat) × 60
```

### 7.2 Çakışma Kontrolü

Her durak için mekanın açılış saatiyle karşılaştırma yapılır:

```
if varış_saati < açılış_saati OR varış_saati > kapanış_saati:
    → "Bu saat kapalı olabilir" uyarısı
```

### 7.3 Süre Optimizasyonu

- Maksimum süre aşılırsa → ziyaret süresi azaltma önerisi
- Tercih edilen bitiş saati geçilirse → erken başlama önerisi
- Tek noktada >120 dk → "çok uzun" uyarısı

---

## 8. Frontend

### 8.1 Kullanılan Teknolojiler

- **Leaflet.js:** Açık kaynaklı interaktif harita kütüphanesi
- **OpenStreetMap Tiles:** Harita görüntüleri
- **Vanilla JavaScript:** Framework bağımsız uygulama mantığı

### 8.2 Özellikler

- Harita üzerinde sürükle-bırak nokta yönetimi
- Rota görselleştirme (renk kodlu segmentler)
- Alternatif rotalar arası geçiş
- POI arama ve görüntüleme
- NLP sorgu arayüzü
- Kaydedilmiş rotalar ve konumlar
- Timeline görselleştirme

---

## 9. API Endpoint'leri

Sistem toplamda **30+** REST API endpoint'i sunar:

| Grup | Sayı | Örnekler |
|------|------|----------|
| Rota | 7 | `POST /api/get-route`, `POST /api/get-alternative-routes` |
| Geocoding | 5 | `GET /api/geocode/suggest`, `POST /api/geocode/batch` |
| NLP | 4 | `POST /api/nlp/parse`, `POST /api/nlp/similarity` |
| Toplu Taşıma | 3 | `POST /api/transit/compare-routes` |
| Hava Durumu | 6 | `GET /api/weather`, `POST /api/weather/check-route` |
| Depolama | 12 | Rota/konum CRUD, favori, arama, istatistik |
| LLM Sohbet | 6 | Gemini ve OpenRouter chat/stream |
| Timeline | 3 | `POST /api/timeline/create`, optimize, çakışma kontrolü |

---

## 10. Test Altyapısı

- **Framework:** Pytest + pytest-cov
- **API Testleri:** Flask test client ile endpoint smoke testleri
- **Core Testleri:** Route engine, config, storage unit testleri
- **BERT Testleri:** Gold dataset (`bert_gold_tr_v1.jsonl`) ile değerlendirme

---

## 11. Kullanılan Kütüphaneler

| Kütüphane | Versiyon | Kullanım Amacı |
|-----------|----------|----------------|
| Flask | 3.1.0 | Web framework |
| OSMnx | 2.0.1 | OpenStreetMap graf indirme |
| NetworkX | 3.4.2 | Graf algoritmaları (Dijkstra, TSP) |
| Transformers | 4.48.0 | BERT model yükleme |
| PyTorch | CUDA 13.0 | GPU hızlandırmalı inference |
| scikit-learn | 1.6.1 | ML yardımcıları |
| Pandas | 2.2.3 | Veri işleme |
| Pydantic | 2.10.4 | Veri doğrulama ve şema |
| Requests | 2.32.3 | HTTP istemcisi |

---

## 12. Algoritma Özet Tablosu

| # | Algoritma | Karmaşıklık | Kullanım |
|---|-----------|-------------|----------|
| 1 | Dijkstra | O((V+E) log V) | En kısa yol |
| 2 | TSP (Christofides) | O(n² · (V+E) log V) | Optimum ziyaret sırası |
| 3 | Via-Node + Penalty | O(K · (V+E) log V) | Alternatif güzergahlar |
| 4 | Asimetrik Edge Overlap | O(n) | Rota farklılık ölçümü |
| 5 | Edge Connectivity (Menger) | O(V · E) | Topoloji ön-analizi |
| 6 | Haversine | O(1) | GPS koordinat mesafesi |
| 7 | R-tree / Grid Index | O(log n) | Mekansal arama |
| 8 | BERT Encoding | O(L² · d) | Metin → vektör |
| 9 | Cosine Similarity | O(n · d) | Anlamsal benzerlik |
| 10 | N-gram Tokenization | O(w²) | Yer ismi çıkarımı |
| 11 | Morfolojik Analiz | O(k) | Türkçe ek soyma |
| 12 | MD5 Hashing | O(1) | Cache key üretimi |
| 13 | Exponential Backoff | O(1) | API retry stratejisi |
| 14 | Zaman Scheduling | O(n) | Zaman çizelgesi |

> **n** = nokta/yer sayısı, **V** = graf düğümü, **E** = kenar, **L** = token uzunluğu, **d** = embedding boyutu (768), **w** = kelime sayısı, **k** = ek sayısı

---

## 13. Sonuç

OpenRoutePlanner, graf teorisi, yapay zeka, mekansal veri işleme ve web teknolojilerini bir arada kullanan kapsamlı bir rota planlama sistemidir. Projede:

- **Dijkstra, TSP ve Via-Node** gibi klasik ve endüstri standardı graf algoritmaları uygulanmıştır
- **BERT tabanlı Türkçe NLP sistemi** ile doğal dilde rota sorgusu imkânı sunulmuştur
- **İBB API entegrasyonu** ile gerçek toplu taşıma verileri kullanılarak multimodal rota planlaması yapılmıştır
- **Çok katmanlı cache mimarisi** ile performans optimize edilmiştir
- **LLM entegrasyonu** (Gemini/OpenRouter) ile yapay zeka sohbet asistanı eklenmiştir
- **Mekansal indeksleme** ile hızlı konum bazlı sorgular gerçekleştirilmiştir

Proje, açık kaynak veri ve araçlar (OpenStreetMap, BERT, Flask) kullanarak ticari alternatiflere (Google Maps) yakın bir kullanıcı deneyimi sunmayı hedeflemektedir.
