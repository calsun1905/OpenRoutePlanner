# BERT Sistem Geliştirme Planı

## Mevcut Durum
✅ Multi-location + Multi-POI segment extraction  
✅ Çoğul ek normalizasyonu (kafeler → kafe)  
✅ OSM entegrasyonu (küçük bölgeler)  
✅ Solo POI desteği  

## Potansiyel Geliştirme Alanları

### 1. Semantik Anlama
```
- "en yakın" → proximity search
- "ucuz" → price range filter
- "kaliteli" → rating filter
```

### 2. Zamanlı Sorgular
```
- "şu an açık mı" → opening hours check
- "gece açık" → late-night filter
- "hafta sonu" → weekend filter
```

### 3. Eşanlamlı Kelime Genişletme
```
kafe ≈ coffee ≈ caffè ≈ kahvehane
restoran ≈ yemek ≈ lokanta ≈ taverna
```

### 4. Hata Toleransı
```
- "kadyköy" → "kadıköy" (typo correction)
- "besiktas" → "beşiktaş" (normalize)
- "kasap dükkanı" → "kasap" (redundancy)
```

### 5. Bağlam Belleği
```
- Önceki sorgu: "Kadıköy'de kafe"
- Sonraki: "orada manav var mı?" → "Kadıköy'de manav"
```

### 6. Duygu Analizi
```
- "en iyi" → sort by rating
- "en ucuz" → sort by price
- "en yakın" → sort by distance
```

### 7. Negatif Filtreleme
```
- "kafe değil" → exclude cafe
- "manav haricinde" → exclude grocery
```

### 8. Öneri Sistemi
```
- "kadıköyde cafe" arandı → "kadıköyde pasta" öner
- Benzer kullanıcıların aramaları
```

---

## Öncelik Sıralaması

| Öncelik | Alan | Açıklama |
|---------|------|----------|
| 🔴 Yüksek | Eşanlamlı kelime genişletme | POI trigger setini büyüt |
| 🔴 Yüksek | Hata toleransı | Typo düzeltme |
| 🟡 Orta | Bağlam belleği | Son sorguyu hatırla |
| 🟡 Orta | Zamanlı sorgular | Açık/kapalı kontrolü |
| 🟢 Düşük | Öneri sistemi | Kullanıcı önerileri |

---

## Örnek Geliştirme: Eşanlamlı Kelime Eşleştirme

```python
# Synonym mapping
_KAFE_SYNONYMS = {
    "kafe", "cafe", "caffè", "coffee", "kahvehane", 
    "çayhane", "pub", "bar", "lounge"
}

def expand_poi_synonyms(poi: str) -> Set[str]:
    """POI için eşanlamlı kelimeleri döndürür."""
    # Doğrudan eşleşme
    synonyms = {poi}
    
    # Synonym group'tan ekle
    for group in _POI_SYNONYM_GROUPS:
        if poi in group:
            synonyms.update(group)
            break
    
    return synonyms
```

---

## Sonraki Adımlar

1. **Hangi geliştirmeyi önce yapalım?**
   - Eşanlamlı kelime genişletme (en hızlı sonuç)
   - Hata toleransı (kullanıcı deneyimi)
   - Bağlam belleği (en değerli)

2. **Mevcut sistemi nasıl test edelim?**
   - Gold dataset ile karşılaştırma
   - Frontend'de canlı test
   - Kullanıcı geri bildirimi

Hangi alana odaklanalım?