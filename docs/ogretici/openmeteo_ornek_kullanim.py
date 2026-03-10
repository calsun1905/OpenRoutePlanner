"""
OpenMeteo API - Örnek Kullanım (Başlangıç Seviyesi)

Bu dosya, OpenMeteo API'sine nasıl bağlanılacağını ve veri alınacağını
adım adım, Türkçe açıklamalarla gösterir.

Çalıştırmak için: python openmeteo_ornek_kullanim.py
Gereksinim: pip install requests
"""

import requests

# =============================================================================
# ADIM 1: Hangi verileri istediğimizi belirliyoruz (3 değişken)
# =============================================================================
# OpenMeteo'dan 3 farklı veri isteyeceğiz:
# 1. Sıcaklık (temperature_2m) - Kaç derece?
# 2. Nem (relative_humidity_2m) - Hava ne kadar nemli? (%)
# 3. Hava durumu kodu (weather_code) - Açık mı, yağmurlu mu? (0=açık, 61=yağmur vb.)

istek_edilen_veriler = "temperature_2m,relative_humidity_2m,weather_code"

# =============================================================================
# ADIM 2: Hangi konum için veri istiyoruz? (Koordinatlar)
# =============================================================================
# Enlem ve boylam = Dünya üzerinde bir noktanın adresi (sayılarla)
# Örnek: 41, 29 = İstanbul civarı

enlem = 41.0      # latitude  - Kuzey/güney konumu (-90 ile 90 arası)
boylam = 29.0     # longitude - Doğu/batı konumu (-180 ile 180 arası)

# =============================================================================
# ADIM 3: API adresini ve parametreleri hazırlıyoruz
# =============================================================================
# OpenMeteo'nun sunucu adresi - bu adrese istek atacağız
api_adresi = "https://api.open-meteo.com/v1/forecast"

# Parametreler = URL'e eklenen bilgiler (hangi konum, ne istiyoruz)
# Bu sözlük, "latitude=41&longitude=29&current=sıcaklık,nem,kod" şeklinde URL'e dönüşecek
parametreler = {
    "latitude": enlem,           # Hangi enlem?
    "longitude": boylam,         # Hangi boylam?
    "current": istek_edilen_veriler   # Hangi veriler? (virgülle ayırarak yazıyoruz)
}

# =============================================================================
# ADIM 4: Bağlantı kuruyoruz ve istek atıyoruz
# =============================================================================
# requests.get() = İnternet üzerinden OpenMeteo sunucusuna "Bu konumda bu verileri ver" diye sorar
# timeout=10 = 10 saniye içinde cevap gelmezse vazgeç (sonsuz bekleme olmasın)

print("OpenMeteo sunucusuna bağlanılıyor...")
print("Konum: Enlem", enlem, ", Boylam", boylam)
print("İstenen veriler: Sıcaklık, Nem, Hava durumu kodu")
print("-" * 50)

try:
    # Bu satır = Gerçek bağlantı. İnternet açıksa ve OpenMeteo çalışıyorsa cevap gelir.
    cevap = requests.get(api_adresi, params=parametreler, timeout=10)
    
    # =============================================================================
    # ADIM 5: Cevabı kontrol ediyoruz
    # =============================================================================
    # status_code = Sunucunun cevabı: 200 = "Tamam, işte veri", 404 = "Bulamadım", 500 = "Sunucu hatası"
    
    if cevap.status_code == 200:
        print("Bağlantı başarılı! (Kod: 200)")
        print("-" * 50)
        
        # =============================================================================
        # ADIM 6: Gelen veriyi Python sözlüğüne çeviriyoruz
        # =============================================================================
        # OpenMeteo JSON formatında veri gönderir. .json() ile Python'da kullanabileceğimiz
        # sözlük (dict) yapısına çeviriyoruz.
        
        veri = cevap.json()
        
        # =============================================================================
        # ADIM 7: İstediğimiz 3 değişkeni çıkarıyoruz
        # =============================================================================
        # veri["current"] = Güncel hava durumu bilgileri
        # İçinden sıcaklık, nem, hava kodu alıyoruz
        
        sicaklik = veri["current"]["temperature_2m"]
        nem = veri["current"]["relative_humidity_2m"]
        hava_kodu = veri["current"]["weather_code"]
        
        # =============================================================================
        # ADIM 8: Sonuçları ekrana yazdırıyoruz
        # =============================================================================
        print("SONUÇLAR (İstediğin 3 değişken):")
        print()
        print("  1. Sıcaklık:", sicaklik, "°C")
        print("  2. Nem:", nem, "%")
        print("  3. Hava durumu kodu:", hava_kodu)
        print()
        
        # Hava kodu açıklaması (0-99 arası sayılar farklı hava durumlarına karşılık gelir)
        hava_aciklamalari = {
            0: "Açık gök yüzü",
            1: "Genellikle açık",
            2: "Parçalı bulutlu",
            3: "Kapalı",
            45: "Sisli",
            61: "Hafif yağmur",
            63: "Orta yağmur",
            95: "Fırtına"
        }
        aciklama = hava_aciklamalari.get(hava_kodu, "Bilinmiyor (kod: " + str(hava_kodu) + ")")
        print("  Hava durumu:", aciklama)
        print()
        print("=" * 50)
        print("Başarıyla tamamlandı!")
        
    else:
        # 200 değilse bir şeyler yanlış gitmiş demektir
        print("Hata! Sunucu kodu:", cevap.status_code)
        print("Cevap:", cevap.text)

except requests.exceptions.ConnectionError:
    # İnternet yok, sunucuya ulaşılamıyor
    print("HATA: İnternet bağlantısı yok veya OpenMeteo sunucusuna ulaşılamıyor!")
    print("İnternet bağlantınızı kontrol edin.")

except requests.exceptions.Timeout:
    # 10 saniye içinde cevap gelmedi
    print("HATA: Sunucu 10 saniye içinde yanıt vermedi!")
    print("Daha sonra tekrar deneyin.")

except Exception as hata:
    # Beklenmeyen başka bir hata
    print("HATA:", str(hata))
