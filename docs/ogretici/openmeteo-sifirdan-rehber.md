# OpenMeteo API - Sıfırdan Başlangıç Rehberi

Bu rehber, OpenMeteo'yu hiç kullanmamış biri için yazılmıştır. Her adımı sırayla takip ederek ilk hava durumu verinizi alabilirsiniz.

---

## Bölüm 1: OpenMeteo Nedir?

**OpenMeteo** = Ücretsiz hava durumu verisi veren bir internet servisi.

- API key gerekmez
- Kayıt gerekmez
- Sadece bir URL'ye istek atarsınız, hava verisi gelir

---

## Bölüm 2: Ne Lazım?

1. **Python** (yüklü olmalı)
2. **requests** kütüphanesi (HTTP isteği atmak için)

```bash
pip install requests
```

---

## Bölüm 3: İlk Bağlantı - Tarayıcıdan Deneme

Kod yazmadan önce, tarayıcıdan test edelim.

### Adım 1: Bu adresi tarayıcıya yapıştırın

```
https://api.open-meteo.com/v1/forecast?latitude=41&longitude=29&current=temperature_2m
```

### Adım 2: Enter'a basın

Ekranda şuna benzer bir metin göreceksiniz:

```json
{
  "latitude": 41.0,
  "longitude": 29.0,
  "current": {
    "time": "2026-03-10T12:00",
    "temperature_2m": 12.9
  }
}
```

**Bu ne demek?**
- `latitude: 41` = Enlem 41 (İstanbul civarı)
- `longitude: 29` = Boylam 29 (İstanbul civarı)
- `temperature_2m: 12.9` = O noktada sıcaklık 12.9°C

**Yani:** Tarayıcı bu URL'ye gitti, OpenMeteo sunucusu cevap verdi. Bağlantı çalışıyor.

---

## Bölüm 4: Python'dan İlk İstek

### Adım 1: Boş bir Python dosyası oluşturun

`test_openmeteo.py` adında bir dosya açın.

### Adım 2: Bu kodu yazın

```python
import requests

# 1. API adresi (OpenMeteo'nun sunucu adresi)
url = "https://api.open-meteo.com/v1/forecast"

# 2. Parametreler (hangi konum, ne istiyoruz)
params = {
    "latitude": 41,
    "longitude": 29,
    "current": "temperature_2m"
}

# 3. İstek at
response = requests.get(url, params=params)

# 4. Cevabı kontrol et
print("Durum kodu:", response.status_code)  # 200 = başarılı
print("Cevap:", response.json())
```

### Adım 3: Çalıştırın

```bash
python test_openmeteo.py
```

### Adım 4: Çıktı

```
Durum kodu: 200
Cevap: {'latitude': 41.0, 'longitude': 29.0, 'current': {'time': '...', 'temperature_2m': 12.9}}
```

**Bu ne demek?**
- `requests.get(url, params=params)` = OpenMeteo sunucusuna "Bu konumda sıcaklık ver" diye istek attık
- `response.status_code = 200` = Sunucu "Tamam, işte veri" dedi
- `response.json()` = Gelen veriyi Python sözlüğüne çevirdik

---

## Bölüm 5: Bağlantı Nasıl Kuruluyor? (Detaylı)

### requests.get() ne yapıyor?

```
Sizin bilgisayarınız                    OpenMeteo sunucusu
        |                                        |
        |  1. "Merhaba, 41,29 koordinatında     |
        |     sıcaklık verir misin?"             |
        |  ---------------------------------->  |
        |                                        |
        |  2. Sunucu veritabanına bakar          |
        |     Hesaplar, hazırlar                 |
        |                                        |
        |  3. "İşte veri: 12.9°C"                |
        |  <----------------------------------  |
        |                                        |
```

**Teknik olarak:**
1. `requests.get()` internet üzerinden OpenMeteo sunucusuna bağlanır
2. HTTP GET isteği gönderir (URL + parametreler)
3. Sunucu cevap hazırlar
4. Cevap geri gelir
5. `response` değişkenine yazılır

**Bağlantı türü:** Geçici. İstek bitince bağlantı kapanır. Kalıcı değil.

---

## Bölüm 6: Hata Durumları

### İnternet yoksa

```python
response = requests.get(url, params=params)
# Hata: requests.exceptions.ConnectionError
```

### Sunucu yanıt vermezse (10 saniye bekledikten sonra)

```python
response = requests.get(url, params=params, timeout=10)
# Hata: requests.exceptions.Timeout
```

### Güvenli kullanım

```python
import requests

url = "https://api.open-meteo.com/v1/forecast"
params = {"latitude": 41, "longitude": 29, "current": "temperature_2m"}

try:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()  # 200 değilse hata fırlat
    data = response.json()
    print("Sıcaklık:", data["current"]["temperature_2m"], "°C")
except requests.exceptions.ConnectionError:
    print("İnternet bağlantısı yok!")
except requests.exceptions.Timeout:
    print("Sunucu yanıt vermedi!")
except Exception as e:
    print("Hata:", e)
```

---

## Bölüm 7: Daha Fazla Veri İsteme

Sadece sıcaklık değil, nem, yağmur, hava kodu da isteyebilirsiniz:

```python
params = {
    "latitude": 41,
    "longitude": 29,
    "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code"
}

response = requests.get(url, params=params)
data = response.json()

current = data["current"]
print("Sıcaklık:", current["temperature_2m"], "°C")
print("Nem:", current["relative_humidity_2m"], "%")
print("Yağış:", current["precipitation"], "mm")
print("Hava kodu:", current["weather_code"])  # 0=açık, 61=yağmur vb.
```

---

## Bölüm 8: Projedeki Kullanım (weather_service.py)

Projenizde bu işlem `weather_service.py` içinde yapılıyor:

| Basit örnek | Projedeki karşılık |
|-------------|---------------------|
| `url = "https://api.open-meteo.com/..."` | `OPENMETEO_BASE_URL` |
| `params = {...}` | `_build_url_current(lat, lon)` ile URL'e ekleniyor |
| `requests.get(url)` | `_fetch_from_openmeteo(url)` |
| `response.json()` | `_parse_current_weather(response)` ile işleniyor |

**Ek olarak projede:**
- Cache var (15 dk aynı veriyi tekrar istemez)
- Hata yönetimi var (NetworkError, RateLimitError)
- WMO kodları Türkçe'ye çevriliyor (0 → "Açık gök yüzü")

---

## Bölüm 9: Özet - İlk Kullanım Checklist

- [ ] `pip install requests` yaptım
- [ ] Tarayıcıda URL'i açıp JSON gördüm
- [ ] Python'da `requests.get(url, params=params)` ile istek attım
- [ ] `response.status_code` 200 döndü
- [ ] `response.json()` ile veriyi aldım

Hepsi tamamsa → OpenMeteo bağlantınız çalışıyor.

---

## Bölüm 10: Hızlı Test Scripti

Aşağıdaki scripti çalıştırarak her şeyin çalıştığını doğrulayabilirsiniz:

```python
# test_ilk_baglanti.py
import requests

def test_openmeteo():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 41,
        "longitude": 29,
        "current": "temperature_2m,weather_code"
    }
    
    print("1. OpenMeteo'ya bağlanılıyor...")
    response = requests.get(url, params=params, timeout=10)
    
    print("2. Durum kodu:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        temp = data["current"]["temperature_2m"]
        code = data["current"]["weather_code"]
        print("3. Başarılı! Sıcaklık:", temp, "°C, Hava kodu:", code)
        return True
    else:
        print("3. Hata! Cevap:", response.text)
        return False

if __name__ == "__main__":
    test_openmeteo()
```

Çalıştırma: `python test_ilk_baglanti.py`
