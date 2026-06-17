# OpenRoute Algoritma Geliştirme Yol Haritası

## Kısa Vadeli İyileştirmeler (1-2 hafta)

### 1. OSM Tag Tabanlı Filtreleme
```python
# graph_manager.py'ye eklenecek
HIGHWAY_PRIORITY = {
    # Sahil/güvenli yollar (tercih et)
    'footway': 1.0,        # Yaya yolu
    'path': 1.0,           # Patika
    'pedestrian': 1.0,     # Yayalaştırılmış cadde
    'steps': 1.2,          # Merdiven (hafif ceza)
    
    # Bağlantı yolları
    'residential': 1.3,    # Konut sokağı
    'unclassified': 1.5,   # Sınıflandırılmamış
    'tertiary': 2.0,       # Üçüncül yol
    
    # Ana yollar (kaçın)
    'secondary': 3.0,
    'primary': 4.0,
    
    # Köprüler (en çok ceza)
    'bridge': 10.0,        # Köprü
}

def apply_highway_penalty(G):
    """Her kenar için ağırlık cezası hesapla"""
    for u, v, key, data in G.edges(keys=True, data=True):
        highway = data.get('highway', '')
        penalty = HIGHWAY_PRIORITY.get(highway, 5.0)
        data['route_weight'] = data.get('length', 100) * penalty
```

### 2. Eğim/Engebe Kontrolü
```python
def calculate_slope_penalty(G):
    """Eğimli yolları cezalandır"""
    for u, v, key, data in G.edges(keys=True, data=True):
        # OSM incline tag'i varsa kullan
        incline = data.get('incline', '')
        if '%' in str(incline):
            slope_pct = float(incline.replace('%', ''))
            if abs(slope_pct) > 8:  # %8'den fazla eğim
                data['route_weight'] *= 2.0
```

### 3. Gece/Güvenlik Modu
```python
def apply_time_penalty(G, is_night=False):
    """Gece saatlerinde karanlık yolları cezalandır"""
    if not is_night:
        return
    
    for u, v, key, data in G.edges(keys=True, data=True):
        # Sokak aydınlatması yoksa
        if data.get('lit') == 'no':
            data['route_weight'] *= 3.0
        # Park veya izole alanlardan kaçın
        area = data.get('landuse', '')
        if 'park' in str(area) or 'forest' in str(area):
            data['route_weight'] *= 2.0
```

---

## Orta Vadeli İyileştirmeler (1-2 ay)

### 4. Makine Öğrenimi ile Rota Tahmini
```python
# Kullanıcı davranışından öğrenme
class RoutePreferenceLearner:
    """
    Kullanıcıların hangi rotaları tercih ettiğini öğrenir.
    Pozitif/negatif geri bildirim toplar.
    """
    def __init__(self):
        self.preferences = {
            'coastal': 0.0,      # Kıyı yolu tercihi
            'shade': 0.0,        # Gölgelik tercihi
            'flat': 0.0,         # Düz yol tercihi
            'crowded': 0.0,      # Kalabalık cadde tercihi
        }
    
    def update_from_feedback(self, route_id, user_liked: bool):
        """Kullanıcı geri bildirimini öğren"""
        route_data = self.get_route_features(route_id)
        for feature, value in route_data.items():
            if feature in self.preferences:
                # Pozitif = o özelliği sevdi
                delta = 0.1 if user_liked else -0.1
                self.preferences[feature] += delta * value
    
    def predict_weight_modifier(self, edge_data):
        """Öğrenilen tercihlere göre ağırlık değiştirici döner"""
        mod = 1.0
        if edge_data.get('coastal'):
            mod *= (1.0 - self.preferences['coastal'] * 0.5)
        if edge_data.get('shade'):
            mod *= (1.0 - self.preferences['shade'] * 0.5)
        return mod
```

### 5. Çoklu Kriterli Karar Verme (MCDA)
```python
# Pareto optimal rotalar bul
def find_pareto_optimal_routes(G, origin, dest, k=5):
    """
    Birden fazla kriter göre en iyi rotaları bul:
    - Mesafe (kısa)
    - Güvenlik (aydınlatma, kalabalık)
    - Manzara (kıyı, park)
    - Zorluk (eğim)
    """
    candidates = []
    
    # Farklı ağırlıklarla rotalar bul
    weights = [
        {'distance': 1.0, 'safety': 0.0, 'scenery': 0.0},
        {'distance': 0.0, 'safety': 1.0, 'scenery': 0.0},
        {'distance': 0.0, 'safety': 0.0, 'scenery': 1.0},
        {'distance': 0.5, 'safety': 0.5, 'scenery': 0.0},
        {'distance': 0.33, 'safety': 0.33, 'scenery': 0.34},
    ]
    
    for w in weights:
        route = weighted_shortest_path(G, origin, dest, w)
        candidates.append({
            'route': route,
            'metrics': calculate_route_metrics(G, route),
            'weights': w
        })
    
    # Pareto frontier'i döndür
    return pareto_filter(candidates)
```

### 6. Real-time Trafik/Robot entegrasyonu
```python
# Overpass API'den canlı veri
def get_live_osm_data(bbox, timeout=30):
    """Anlık yol durumu (kapalı yollar, etkinlikler)"""
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:{timeout}];
    (
      node["highway"]["highway"!="crossing"]({bbox});
      way["highway"]["access"!="no"]({bbox});
    );
    out body;
    """
    # Bu verileri cache'le ve periyodik güncelle
```

---

## Uzun Vadeli İyileştirmeler (3-6 ay)

### 7. Graph Neural Network Tabanlı Yol Tahmini
```python
# GNN ile yol kalitesi tahmini
class RouteQualityGNN(nn.Module):
    """
    Graph Attention Network ile yol kalitesi tahmini.
    Eğitim için binlerce kullanıcı rotası gerekir.
    """
    def __init__(self):
        self.conv1 = GATConv(8, 16)   # OSM özellikleri
        self.conv2 = GATConv(16, 8)  # Komşu node'lar
        self.fc = nn.Linear(8, 1)    # Kalite skoru
    
    def forward(self, G):
        # Node özellikleri: [length, slope, highway_type, lit, surface, ...]
        x = self.extract_node_features(G)
        x = F.relu(self.conv1(x, G.edge_index))
        x = F.relu(self.conv2(x, G.edge_index))
        return self.fc(x)
```

### 8. Adaptive Routing (Dinamik Yol Bulma)
```python
class AdaptiveRouter:
    """
    Kullanıcının hızına, zamanına, preferanslarına
    göre rotayı dinamik olarak ayarlar.
    """
    def __init__(self, user_profile):
        self.user = user_profile
        self.current_speed = 0  # m/s
        self.remaining_time = user_profile.total_time
        self.route_so_far = []
    
    def should_recalculate(self, current_pos):
        """
        Mevcut rotayı yeniden hesaplamaya gerek var mı?
        """
        # Sapma kontrolü
        expected_pos = self.route_so_far[-1]
        deviation = haversine(current_pos, expected_pos)
        
        # Zaman kontrolü
        time_used = self.calculate_time_used()
        
        return deviation > 50 or time_used > self.remaining_time * 0.8
    
    def reroute(self, G, current_pos, destination):
        """Yeni rota hesapla"""
        return find_optimal_route(
            G, current_pos, destination,
            time_budget=self.remaining_time,
            user_preferences=self.user.preferences
        )
```

### 9. Augmented Reality Entegrasyonu
```python
# AR ile yaya navigasyonu
class ARNavigationOverlay:
    """
    Kamera görüntüsü üzerine yol tarifi bindirme.
    Kaldırım kenarlarını, yaya geçitlerini tespit eder.
    """
    def detect_sidewalks(frame):
        """Görüntüden kaldırım tespiti"""
        # OpenCV/CV2 ile edge detection
        # Deep learning model (YOLO) ile nesne tespiti
        pass
    
    def overlay_direction(frame, route_instruction):
        """Yön okunu görüntüye bindir"""
        # 3D ok render
        # Sesli yönlendirme
        pass
```

---

## Öncelik Matrisi

| Öncelik | İyileştirme | Etki | Zorluk | Maliyet |
|---------|--------------|------|--------|---------|
| 🔴 P1 | OSM Tag Filtreleme | Orta | Düşük | Ücretsiz |
| 🔴 P1 | Köprü Cezası | Yüksek | Düşük | Ücretsiz |
| 🟡 P2 | Eğim Kontrolü | Orta | Orta | Ücretsiz |
| 🟡 P2 | Pareto Rotalar | Yüksek | Yüksek | Orta |
| 🟡 P2 | Makine Öğrenimi | Çok Yüksek | Çok Yüksek | Yüksek |
| 🟢 P3 | GNN Tabanlı | Çok Yüksek | Çok Yüksek | Çok Yüksek |
| 🟢 P3 | AR Entegrasyonu | Yüksek | Çok Yüksek | Çok Yüksek |

---

## Hangi Özelliği Önce Yapmalı?

**Tavsiye:** Önce "Köprü Cezası" ile başlayın:
1. En az kod değişikliği
2. Kullanıcı deneyiminde en belirgin fark
3. Test edilmesi kolay

Sonra sırasıyla:
1. OSM Tag Filtreleme (1 gün)
2. Eğim Kontrolü (2 gün)  
3. Pareto Rotalar (1 hafta)
4. Makine Öğrenimi (2-4 hafta)
