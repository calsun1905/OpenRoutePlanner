# OSMnx Hata Düzeltmesi

## 🐛 Hata
```
AttributeError: module 'osmnx' has no attribute 'config'
```

## 🔍 Neden Oluyor?

OSMnx kütüphanesinin eski versiyonu yüklü. OSMnx 2.0+ versiyonunda API değişti:

- ❌ Eski: `ox.config()`
- ✅ Yeni: `ox.settings`

## ✅ Çözüm

### Adım 1: OSMnx Versiyonunu Kontrol Et
```bash
pip show osmnx
```

**Beklenen:** Version: 2.0.1 veya üzeri

### Adım 2: OSMnx'i Güncelle
```bash
pip install --upgrade osmnx
```

### Adım 3: Bağımlılıkları Güncelle
```bash
cd OpenRoutePlanner/backend
pip install -r ../requirements.txt --upgrade
```

### Adım 4: Backend'i Yeniden Başlat
```bash
# Ctrl+C ile durdur
# Sonra tekrar başlat
python app.py
```

---

## 🔧 Alternatif Çözüm: Temiz Kurulum

Eğer yukarıdaki çalışmazsa:

```bash
# 1. Virtual environment'ı sil
rm -rf .venv

# 2. Yeni virtual environment oluştur
python -m venv .venv

# 3. Aktif et
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 4. Bağımlılıkları yükle
pip install -r requirements.txt

# 5. Backend'i başlat
cd backend
python app.py
```

---

## 📋 requirements.txt Kontrolü

`requirements.txt` dosyasında şu satır olmalı:

```
osmnx==2.0.1
```

Eğer farklı bir versiyon yazıyorsa (örn: `osmnx==1.x.x`), düzelt:

```bash
# requirements.txt'i düzenle
osmnx==2.0.1  # Bu satırı güncelle

# Sonra yükle
pip install -r requirements.txt --upgrade
```

---

## 🧪 Test Et

```bash
# Python console'da test et
python
>>> import osmnx as ox
>>> print(ox.__version__)
2.0.1  # veya üzeri olmalı
>>> ox.settings  # Hata vermemeli
>>> exit()
```

---

## ⚠️ Yaygın Sorunlar

### Sorun 1: "No module named 'osmnx'"
```bash
# Çözüm: Yükle
pip install osmnx==2.0.1
```

### Sorun 2: "Could not find a version that satisfies"
```bash
# Çözüm: pip'i güncelle
python -m pip install --upgrade pip
pip install osmnx==2.0.1
```

### Sorun 3: "Permission denied"
```bash
# Çözüm: Admin olarak çalıştır veya --user kullan
pip install --user osmnx==2.0.1
```

---

## 🎯 Hızlı Çözüm (Tek Komut)

```bash
pip install --upgrade osmnx networkx
```

Sonra backend'i yeniden başlat!

---

## ✅ Başarı Kontrolü

Backend başlatıldığında şu mesajı görmeli:

```
==================================================
  OpenTrip API Sunucusu Başlatılıyor...
  http://localhost:5000
==================================================
 * Running on http://127.0.0.1:5000
```

Eğer hata mesajı yoksa, başarılı! 🎉

---

## 📊 Versiyon Uyumluluğu

| Paket | Minimum Versiyon | Önerilen |
|-------|------------------|----------|
| osmnx | 2.0.0 | 2.0.1 |
| networkx | 3.0 | 3.4.2 |
| geopandas | 0.14.0 | latest |

---

## 🆘 Hala Çalışmıyor?

1. Virtual environment kullanıyor musun?
2. Python versiyonu 3.9+ mı?
3. pip güncel mi? (`pip --version`)

```bash
# Tüm bağımlılıkları kontrol et
pip list | grep -E "osmnx|networkx|geopandas"
```

Sonuçları gönder, yardımcı olalım!
