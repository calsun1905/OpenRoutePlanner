from transformers import pipeline
import time

print("="*60)
print("🤖 BERT MODELİ NASIL ÇALIŞIR? BASİT ÖRNEK")
print("="*60)
print("\nAdım 1: Modeli Hugging Face'ten yüklüyoruz (Cache'den varsa oradan)...")

# Hugging Face model adı - İlk seferde indirir, sonra cache'den yükler
MODEL_ADI = "dbmdz/bert-base-turkish-uncased"

# Hugging Face 'pipeline' aracı, modeli kullanmanın en basit yoludur.
baslangic_zamani = time.time()
try:
    # fill-mask: BERT'in en temel görevi olan "nokta noktalı yeri tahmin etme" görevidir.
    # Biz bunu sadece modelin "Türkçe anladığını" göstermek için kullanıyoruz.
    nlp_tahmin = pipeline("fill-mask", model=MODEL_ADI)
    print(f"✅ Model hazır! (Yüklenme süresi: {time.time() - baslangic_zamani:.2f} saniye)")
except Exception as e:
    print(f"❌ HATA: Model klasörde bulunamadı veya yüklenemedi. Detay: {e}")
    exit()

print("\n" + "="*60)
print("Adım 2: Modele Türkçe bir cümle veriyoruz ve boşluğu doldurmasını istiyoruz.")
print("Kural: Cümle içinde [MASK] yazan yeri model kendisi tahmin edecek.")
print("="*60)

# Burada BERT'e bir zorluk veriyoruz. Anlamına göre boşluğu doğru kelimeyle mi dolduracak?
ornek_cumleler = [
    # Mekan / Lokasyon algısı
    "Kadıköy'den vapura binip [MASK] iskelesinde indim.",
    "Burası çok sıcak, lütfen [MASK] açar mısın?",
    "Bugün hava çok güzel, biraz [MASK] çıkalım.",
    "İstanbul'da trafik çok [MASK], yetişemeyeceğim.",
    
    # Rota ve yön algısı
    "Ankara'dan İstanbul'a arabayla gitmek [MASK] saat sürer.",
    "Yol çok kalabalık, başka bir [MASK] bulalım.",
    
    # Restoran / Etkinlik bağlamı
    "Akşam yemeği için güzel bir [MASK] arıyorum.",
    "Ronaldo ve Messi [MASK] futbolcularıdır.",
    
    # Duygu / Durum algısı
    "Bu projeyi bitirdiğim için çok [MASK] hissediyorum.",
    "Sınavdan düşük aldığım için biraz [MASK]."
]

for cumle in ornek_cumleler:
    print(f"\nSorduğumuz Cümle: {cumle}")
    print("Modelin Tahminleri (Yüzde ihtimalle):")
    print("-" * 40)
    
    # Modele cümleyi veriyoruz
    sonuclar = nlp_tahmin(cumle)
    
    # Sadece en iyi 3 tahmini ekrana yazdırıyoruz
    for tahmin in sonuclar[:3]:
        kelime = tahmin['token_str']
        ihtimal = tahmin['score'] * 100
        print(f"-> %{ihtimal:.1f} ihtimalle: '{kelime}' olmalı.")
    
print("\n" + "="*60)
print("💡 GÖRDÜĞÜNÜZ GİBİ:")
print("Model sadece kelimeleri değil, cümlenin gelişinden 'baglamı' anlayabiliyor.")
print("İşte nlp_engine.py içinde rotaları anlarken yapacağımız şey de bu zekayı kullanmak.")
print("="*60)
