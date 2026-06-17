# Backend Entegrasyonu için Gerekli Veriler

## 1. Şu An Hazır Olanlar

| Veri | Durum | Açıklama |
|------|-------|----------|
| 37 İstanbul İlçesi | ✅ Hazır | Koordinatları (lat/lon) var |
| 37 POI Tag | ✅ Hazır | OSM formatında eşleştirme |
| Çoğul normalizasyonu | ✅ Hazır | kafeler→kafe |
| Türkçe karakter desteği | ✅ Hazır | ş→s, ı→i |

## 2. Sizden İstenen Veriler

### A. POI Veritabanı (Önemli ⚠️)

**Sorun:** Overpass/Nominatim API rate limit nedeniyle çalışmıyor.
**Çözüm:** Kendi POI veritabanınızı oluşturmanız gerekiyor.

**İki seçenek:**

#### Seçenek 1: OSM Veri İndir (Önerilen)
```
İstanbul POI verisi için:
1. https://download.geofabrik.de/turkey.html adresinden
2. "istanbul-latest.osm.pbf" dosyasını indir
3. Bunu kendi veritabanınıza import et
```

#### Seçenek 2: Manuel Veri Girişi
```python
# Size bir veri formatı vereyim, Excel/CSV olarak doldurun
POI_DB = {
    "kadikoy": [
        {"name": "...", "lat": ..., "lon": ..., "type": "cafe", "address": "..."},
        {"name": "...", "lat": ..., "lon": ..., "type": "restaurant", "address": "..."},
    ]
}
```

### B. Backend Endpoint URL'si

```
POST /api/nlp/parse
POST /api/poi/search

Sizin backend'in hangi URL'lerde çalışıyor?
Ör: http://localhost:5000/api/nlp/parse
```

### C. Veritabanı Tipi (Opsiyonel)

| Tip | Avantaj | Dezavantaj |
|-----|---------|------------|
| PostgreSQL + PostGIS | ✅ Entegrasyon kolay | Kurulum gerekli |
| SQLite | ✅ Hızlı kurulum | Büyük veri için yavaş |
| MongoDB | ✅ Esnek şema | Kurulum gerekli |
| CSV/JSON | ✅ En basit | Sorgulama yavaş |

## 3. Hangi Veriyi İstersiniz?

### Minimum (Çalışması için):
1. **POI veritabanı** - En az 5-10 lokasyon için örnek veri
2. **Backend URL** - API endpoint adresi

### İdeal (Tüm özellikler için):
1. **OSM veritabanı** - İstanbul'un tamamı için
2. **Koordinat verisi** - Her ilçe için (zaten var)
3. **POI veritabanı** - Her POI türü için

## 4. Size Önereceğim Format

Excel dosyası olarak bu formatta veri hazırlayabilir misiniz?

| ilçe | name | lat | lon | type | address | phone |
|------|------|-----|-----|------|---------|-------|
| kadıköy | Starbucks Moda | 40.991 | 29.027 | cafe | Moda Cd. | - |
| kadıköy | MMM Mantı | 40.990 | 29.025 | restaurant | Caferağa Mah. | - |
| beşiktaş | Kahve Dünyası | 41.044 | 29.010 | cafe | Akaretler | - |

---

**Ne yapmamı istersiniz?**
1. Veri formatı oluşturup Excel şablonu vereyim
2. Siz veri girişi yapın, ben import scripti yazayım
3. Mevcut mock veritabanını genişleteyim
4. OSM veritabanı kurulum scripti yazayım