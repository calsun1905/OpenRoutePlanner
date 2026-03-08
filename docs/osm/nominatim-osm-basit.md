# Nominatim ve OSM - Basit Anlatım

---

## 🎯 En Basit Haliyle

**OSM = Veritabanı**
**Nominatim = Arama Motoru**

---

## 📚 Google Benzetmesi

Düşün ki OSM, Google'ın indexlediği tüm **web siteleri** gibi.
Nominatim da **Google arama motoru** gibi.

```
        ┌─────────────────────────────────────┐
        │      GOOGLE (Web Siteleri)          │
        │  Milyonlarca web sitesi verisi      │
        └─────────────────────────────────────┘
                        ↓
              Google Arama Motoru
         "facebook" yaz → bulur

        ┌─────────────────────────────────────┐
        │         OSM (Harita Verisi)         │
        │  Milyonlarca yer ismi verisi        │
        └─────────────────────────────────────┘
                        ↓
              Nominatim Arama Motoru
         "Kadıköy" yaz → bulur
```

---

## 🔍 Örnek Senaryo

### Senin sorunun:
> "Kadıköy Parkı'nın koordinatları nedir?"

### OSM (Veritabanı) şunu der:
> "Benim içinde milyonlarca yer var. Hangi Kadıköy Parkı? Arama yapman lazım."

### Nominatim (Arama Motoru) devreye girer:
```
1. Sen: "Kadıköy Parkı" yaz
2. Nominatim: OSM veritabanında ara
3. Nominatim: Buldum! İşte koordinatları: [40.985, 29.025]
```

---

## 📮 Postane Benzetmesi

Daha da basitleştirelim:

```
OSM        = Dev arşiv odası (milyonlarca dosya)
Nominatim  = Arşiv görevlisi

Sen: "Kadıköy Parkı dosyasını bul"
Görevli (Nominatim): Arşive gider → arar → bulur → getirir
```

---

## 💻 Kod ile Görelim

```python
# Nominatim API'sini kullanıyoruz (bu bir web servisi)
# OSM veritabanını aramak için

import requests

# Arama yapıyoruz
url = "https://nominatim.openstreetmap.org/search"
cevap = requests.get(url, params={"q": "Kadıköy Parkı", "format": "json"})

print(cevap.json())
```

**Çıktı:**
```json
[
  {
    "lat": "40.9850",    ← Enlem
    "lon": "29.0250",    ← Boylam
    "name": "Kadıköy Parkı, Kadıköy, İstanbul"
  }
]
```

---

## 🎨 Görsel

```
┌─────────────────────────────────────────────────────────────┐
│                      OSM VERİTABANI                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Kadıköy   │  │Beşiktaş  │  │İstinye   │  │Taksim... │   │
│  │Parkı     │  │Parkı     │  │Park      │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Bağdat    │  │Barbaros  │  │Rumeli    │  │...       │   │
│  │Caddesi   │  │Bulvarı   │  │Hisarı    │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                      ... ... ...                            │
└─────────────────────────────────────────────────────────────┘
                            ↑
                            │
                    ┌───────┴────────┐
                    │  NOMINATIM     │  ← Sen buraya soruyorsun
                    │  Arama Motoru  │
                    └────────────────┘

Sen: "Kadıköy Parkı nerede?"
Nominatim: OSM'ye sor → cevabı bul → sana ver
```

---

## 🆚 Karşılaştırma

| Özellik | OSM | Nominatim |
|---------|-----|-----------|
| **Ne?** | Veritabanı | Arama motoru |
| **İçinde ne var?** | Tüm dünya harita verisi | Arama yapabilen yazılım |
| **Ne yapar?** | Veri saklar | Veri arar |
| **Benzeri** | Wikipedia | Google Arama |
| **Projenizde** | Dolaylı kullanıyoruz | Yeni ekleyeceğiz |

---

## 🎯 Tekrar Özet

```
OSM       = Kitaplık (tüm kitaplar)
Nominatim = Kütüphaneci (kitap bulan kişi)

Sen: "Kadıköy Parkı kitabını bul"
Kütüphaneci (Nominatim): Raflara bakar → bulur → getirir
```

---

## 💡 Neden İkisine de İhtiyacımız Var?

OSM'nin içinde veri var ama **arama yapamıyoruz**. Sadece indirip kullanabiliyoruz.

Nominatim ise **OSM'yi aramamızı sağlıyor.**

```
OSM alone:    "Koordinat ver, sana bilgi veririm"
Nominatim:    "İsim ver, sana koordinat bulayım"
```

---

## 🔗 Gerçek Hayat Örneği

### Şu an projenizde ne oluyor?

```python
# Mevcut durum - SENSİN koordinat veriyorsun
points = [[40.990, 29.029], [40.985, 29.025]]  # Sen elle yazdın

# Yeni durum - İSİM vererek sorgu yapacaksın
query = "Kadıköy'den Kadıköy Parkı'na"
# Nominatim: "Kadıköy" → [40.990, 29.029]
# Nominatim: "Kadıköy Parkı" → [40.985, 29.025]
```

---

Anlaşıldı mı? Sadece şunu bil:
- **OSM = Veri deposu**
- **Nominatim = Arama motoru (bu veride arama yapar)**
