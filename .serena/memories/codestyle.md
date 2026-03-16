# OpenRoutePlanner - Code Style ve Conventions

## 🐍 Python Code Style (Backend)

### Genel
- **Encoding:** UTF-8 (Türkçe karakterler için)
- **Indentation:** 4 spaces (tab yok)
- **Line Length:** ~88-100 (açıkça belirlenmemiş, pratikte 88-120)
- **Import Style:** PEP 8 (standard library → third-party → local)

### İsimlendirme
```python
# Fonksiyonlar: snake_case
def get_route():
def solve_tsp():
def build_alternative_routes():

# Değişkenler: snake_case
route_data
alternative_routes
selected_points

# Sabitler: UPPER_SNAKE_CASE (route_config.py)
DEFAULT_PENALTY_FACTOR = 2.0
MIN_VIA_NODE_DEGREE = 3

# Sınıflar: PascalCase (yok denecek kadar az)
class RouteEngine:  # teorik olarak

# Modüller: snake_case
route_engine.py
graph_manager.py
bert_nlp_engine.py
```

### Type Hints
- **Durum:** Kısmen kullanılıyor (tutarlı değil)
- **Örnek:**
```python
def solve_tsp(points: List[Tuple[float, float]]) -> List[int]:
    pass

# Bazı fonksiyonlarda yok:
def get_graph():
    pass  # type hint yok
```

### Docstrings
- **Durum:** Çoğu fonksiyonda docstring yok
- **Format:** Google style (var olanlarda)
```python
def solve_tsp(points, graph):
    """
    TSP'yi çöz - en kısa rota sırasını bul.
    
    Args:
        points: (lat, lon) listesi
        graph: NetworkX graf
        
    Returns:
        Sıralı nokta indeksleri listesi
    """
```

### Hata Yönetimi
```python
# Genel pattern
try:
    result = some_operation()
except Exception as e:
    logger.error(f"Hata: {e}")
    return None

# Specific exceptions (bazı yerlerde)
except ValueError as e:
    ...
except KeyError as e:
    ...
```

### Logging
- **Dosya:** `backend_errors.log`
- **Format:** File-based logging (app.py)
- **Örnek:**
```python
import logging
logging.basicConfig(
    filename='backend_errors.log',
    level=logging.ERROR
)
```

### Cache Pattern
- **Global değişkenler:** `_graph_cache`, `_poi_cache`
- **Pattern:**
```python
_graph_cache = {}

def get_graph(location):
    if location in _graph_cache:
        return _graph_cache[location]
    
    graph = download_graph(location)
    _graph_cache[location] = graph
    return graph
```

### Singleton Pattern (BERT)
```python
# bert_engine.py
_model = None
_tokenizer = None

def get_model():
    global _model, _tokenizer
    if _model is None:
        _model = load_model()
        _tokenizer = load_tokenizer()
    return _model, _tokenizer
```

## 🌐 JavaScript Code Style (Frontend)

### Genel
- **Style:** Vanilla JavaScript (framework yok)
- **Pattern:** Functional + bazı state management
- **Event handling:** Direct DOM manipulation

### İsimlendirme
```javascript
// Değişkenler: camelCase
const selectedPoints = [];
const currentRouteData = null;
const alternativeRoutesCache = {};

// Fonksiyonlar: camelCase
function calculateRoute() {}
function displayAlternativeRoutes() {}
function updateButtons() {}

// Sabitler: UPPER_SNAKE_CASE (çok az)
const MAX_POINTS = 10;

// CSS class'ler: kebab-case
.selected-point
.route-button
```

### State Management
```javascript
// Global STATE objesi
const STATE = {
    selectedPoints: [],
    currentRouteData: null,
    alternativeRoutes: [],
    alternativeRoutesCache: {},  // ⚠️ Bu eksikti, sonradan eklendi
    // ...
};
```

### Async Pattern
```javascript
// Fetch ile API çağrısı
async function calculateRoute() {
    const response = await fetch('/api/get-route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ points: STATE.selectedPoints })
    });
    const data = await response.json();
    return data;
}
```

### Event Listeners
```javascript
// Pattern
document.getElementById('button-id').addEventListener('click', functionName);

// Inline (bazen)
<button onclick="calculateRoute()">Rota Hesapla</button>
```

## 🎨 CSS Style

### İsimlendirme
```css
/* BEM-like (resmi değil, pratikte) */
.route-button { }
.route-button--disabled { }
.selected-point { }
.map-container { }

/* Leaflet overrides */
.leaflet-container { }
```

### Units
- **Spacing:** px (bazen rem)
- **Font:** px
- **Colors:** hex (#e5e5e5)
- **Borders:** px

## 📝 Comments

### Python
```python
# Tek satır (genelde)
# Çoklu satır (bazen)

# TODO: Yapılacak iş
# FIXME: Düzeltilecek bug
# HACK: Geçici çözüm
```

### JavaScript
```javascript
// Tek satır
/* Çoklu satır (bazen) */

// TODO: Yapılacak iş
// FIXME: Düzeltilecek bug
```

## 🚫 Anti-Patterns (Gözlemlenen)

1. **Global state:** Python'da `_graph_cache` gibi global değişkenler
2. **Error swallowing:** `except: pass` pattern'i (bazı yerlerde)
3. **No type hints:** Çoğu fonksiyonda type hint yok
4. **Mixed logging:** Print'ler ve logging karışık
5. **Hardcoded values:** Çok sayıda magic number (route_config.py ile çözülmeye çalışıldı)

## ✅ Best Practices (Kullanılan)

1. **Cache:** OSM graf ve POI cache
2. **Singleton:** BERT model için singleton pattern
3. **Rate limiting:** Nominatim API için 1 req/s
4. **Modüler yapı:** Her modül ayrı dosyada
5. **Progress tracking:** `progress.md` ile detaylı takip
6. **Documentation:** API_ENDPOINTS.md, PROJECT_INDEX.md gibi dokümanlar

## 📌 Notlar

1. **Type hints:** İyileştirilmeli (mypy ile kontrol edilebilir)
2. **Docstrings:** Standart hale getirilmeli
3. **Error handling:** Spesifik exception'lar kullanılmalı
4. **Logging:** Loglama standardize edilmeli
5. **Testing:** Test coverage artırılmalı
