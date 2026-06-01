"""
BERT Semantik Test - Modelin gerçekten ne kadar "anlıyor" olduğunu görüyoruz.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from bert_engine import get_bert_engine

engine = get_bert_engine()

print("=" * 65)
print("🧪 BERT SEMANTİK TEST - dbmdz/bert-base-turkish-uncased")
print("=" * 65)

# =========================================================================
# TEST 1: AYNI KELİME - BİREBİR EŞLEŞME
# =========================================================================
print("\n" + "─" * 65)
print("TEST 1: Aynı kelime (1.0 olmalı)")
print("─" * 65)
pairs = [
    ("Kadıköy", "Kadıköy"),
    ("Beşiktaş", "Beşiktaş"),
    ("Taksim", "Taksim"),
]
for a, b in pairs:
    sim = engine.similarity(a, b)
    durum = "✅" if sim > 0.95 else "⚠️"
    print(f"  {durum} '{a}' vs '{b}' → {sim:.4f}")

# =========================================================================
# TEST 2: BÜYÜK/KÜÇÜK HARF (uncased avantajı)
# =========================================================================
print("\n" + "─" * 65)
print("TEST 2: Büyük/küçük harf (uncased sayesinde yüksek olmalı)")
print("─" * 65)
pairs = [
    ("Kadıköy", "KADIKÖY"),
    ("Beşiktaş", "beşiktaş"),
    ("Taksim", "TAKSIM"),
    ("İstanbul", "istanbul"),
]
for a, b in pairs:
    sim = engine.similarity(a, b)
    durum = "✅" if sim > 0.90 else "⚠️"
    print(f"  {durum} '{a}' vs '{b}' → {sim:.4f}")

# =========================================================================
# TEST 3: TYPO / YANLIŞ YAZIM
# =========================================================================
print("\n" + "─" * 65)
print("TEST 3: Typo toleransı (yanlış yazılmış kelimeler)")
print("─" * 65)
pairs = [
    ("Kadıköy", "Kadikoy"),  # Türkçe karakter yok
    ("Beşiktaş", "Besiktas"),  # Türkçe karakter yok
    ("Üsküdar", "Uskudar"),  # Türkçe karakter yok
    ("Şişli", "Sisli"),  # Türkçe karakter yok
    ("Mecidiyeköy", "Mecidiyekoy"),  # Türkçe karakter yok
    ("Kadıköy", "kadiköy"),  # K harfi farklı
    ("Taksim", "Taxsim"),  # Harf değişimi
]
for a, b in pairs:
    sim = engine.similarity(a, b)
    durum = "✅" if sim > 0.85 else "⚠️ DÜŞÜK"
    print(f"  {durum} '{a}' vs '{b}' → {sim:.4f}")

# =========================================================================
# TEST 4: FARKLI YERLER (düşük benzerlik olmalı)
# =========================================================================
print("\n" + "─" * 65)
print("TEST 4: Farklı yer isimleri (düşük olmalı)")
print("─" * 65)
pairs = [
    ("Kadıköy", "Beşiktaş"),
    ("Taksim", "Üsküdar"),
    ("İstanbul", "Ankara"),
    ("Kadıköy", "Antalya"),
]
for a, b in pairs:
    sim = engine.similarity(a, b)
    durum = "✅" if sim < 0.80 else "⚠️ YÜKSEK"
    print(f"  {durum} '{a}' vs '{b}' → {sim:.4f}")

# =========================================================================
# TEST 5: SEMANTİK BENZERLİK (anlamca yakın)
# =========================================================================
print("\n" + "─" * 65)
print("TEST 5: Anlamca benzeyen kelime/cümleler")
print("─" * 65)
pairs = [
    ("Taksim Meydanı", "Taksim"),
    ("Kadıköy", "Kadıköy ilçesi"),
    ("Beşiktaş", "Beşiktaş semti"),
    ("rota planla", "yol tarifi ver"),
    ("nasıl giderim", "rotam ne olmalı"),
]
for a, b in pairs:
    sim = engine.similarity(a, b)
    durum = "✅" if sim > 0.75 else "⚠️"
    print(f"  {durum} '{a}' vs '{b}' → {sim:.4f}")

# =========================================================================
# TEST 6: ANLAMSIZ KELİMELER (düşük olmalı)
# =========================================================================
print("\n" + "─" * 65)
print("TEST 6: Alakasız kelimeler (düşük olmalı)")
print("─" * 65)
pairs = [
    ("Kadıköy", "merhaba"),
    ("rota", "teşekkürler"),
    ("Beşiktaş", "hava güzel"),
    ("Taksim", "nasılsın"),
]
for a, b in pairs:
    sim = engine.similarity(a, b)
    durum = "✅" if sim < 0.70 else "⚠️ YÜKSEK"
    print(f"  {durum} '{a}' vs '{b}' → {sim:.4f}")

# =========================================================================
# TEST 7: POI / MEKAN İSİMLERİ
# =========================================================================
print("\n" + "─" * 65)
print("TEST 7: POI / Mekan eşleşmeleri")
print("─" * 65)
pairs = [
    ("kafe", "kahve"),
    ("restoran", "lokanta"),
    ("hastane", "eczane"),
    ("müze", "sergi"),
    ("park", "bahçe"),
    ("cami", "kilise"),
]
for a, b in pairs:
    sim = engine.similarity(a, b)
    durum = "✅" if sim > 0.60 else "⚠️"
    print(f"  {durum} '{a}' vs '{b}' → {sim:.4f}")

# =========================================================================
# TEST 8: INTENT (niyet) anlama
# =========================================================================
print("\n" + "─" * 65)
print("TEST 8: Intent - sorgu tipi anlama")
print("─" * 65)

# Route intent vs POI intent
route_sorgu = "Kadıköy'den Beşiktaş'a nasıl giderim"
poi_sorgu = "Kadıköy'de kafe var mı"

route_template = "Kadıköy'den Beşiktaş'a rota"
poi_template = "Kadıköy'de neler var"

sim_route_vs_route = engine.similarity(route_sorgu, route_template)
sim_route_vs_poi = engine.similarity(route_sorgu, poi_template)
sim_poi_vs_poi = engine.similarity(poi_sorgu, poi_template)
sim_poi_vs_route = engine.similarity(poi_sorgu, route_template)

print(
    f"  Route sorgu vs Route template → {sim_route_vs_route:.4f} {'✅' if sim_route_vs_route > 0.80 else '⚠️'}"
)
print(
    f"  Route sorgu vs POI template   → {sim_route_vs_poi:.4f} {'✅' if sim_route_vs_poi < 0.80 else '⚠️'}"
)
print(
    f"  POI sorgu vs POI template     → {sim_poi_vs_poi:.4f} {'✅' if sim_poi_vs_poi > 0.80 else '⚠️'}"
)
print(
    f"  POI sorgu vs Route template   → {sim_poi_vs_route:.4f} {'✅' if sim_poi_vs_route < 0.80 else '⚠️'}"
)

# =========================================================================
# TEST 9: CLS vs MEAN pooling karşılaştırma
# =========================================================================
print("\n" + "─" * 65)
print("TEST 9: CLS vs Mean Pooling karşılaştırma")
print("─" * 65)

test_pairs_pool = [
    ("Kadıköy", "Kadikoy"),
    ("Taksim", "TAKSIM"),
    ("rota planla", "yol tarifi ver"),
]
for a, b in test_pairs_pool:
    sim_cls = engine.similarity(a, b, pooling_strategy="cls")
    sim_mean = engine.similarity(a, b, pooling_strategy="mean")
    fark = sim_mean - sim_cls
    daha_iyi = "MEAN ✅" if sim_mean > sim_cls else "CLS ✅"
    print(f"  '{a}' vs '{b}'")
    print(f"    CLS:  {sim_cls:.4f}")
    print(f"    MEAN: {sim_mean:.4f}  ({fark:+.4f}) → {daha_iyi}")

# =========================================================================
# TEST 10: UZUN CÜMLE SEMANTİĞİ
# =========================================================================
print("\n" + "─" * 65)
print("TEST 10: Uzun cümle semantiği")
print("─" * 65)

sorgu = "Kadıköy'den Beşiktaş'a rota çiz"
pairs = [
    (sorgu, "Kadıköy Beşiktaş arası yol tarifi"),
    (sorgu, "Kadıköy'de ne var"),
    (sorgu, "Merhaba nasılsın"),
    (sorgu, "İstanbul'da yaşiyorum"),
    (sorgu, "Taksim'e gitmek istiyorum"),
]
for a, b in pairs:
    sim = engine.similarity(a, b)
    durum = "✅" if sim > 0.60 else "⚠️"
    print(f"  {durum} sim={sim:.4f} '{b}'")

# =========================================================================
# GENEL DEĞERLENDİRME
# =========================================================================
print("\n" + "=" * 65)
print("📊 GENEL DEĞERLENDİRME")
print("=" * 65)
print(
    """
  ✅ = Beklendiği gibi çalışıyor
  ⚠️ = Düşük performans / iyileştirilebilir

  Yukarıdaki sonuçlara göre:
  - Aynı kelime: ~1.0 olmalı
  - Typo: ~0.85+ olmalı
  - Farklı yerler: ~0.70- olmalı
  - Anlamca yakın: ~0.75+ olmalı
  - Alakasız: ~0.60- olmalı
"""
)

from bert_engine import get_embedding_cache_stats

stats = get_embedding_cache_stats()
print(
    f"  Cache: hits={stats['cache_hits']}, misses={stats['cache_misses']}, "
    f"size={stats['cache_size']}, hit_rate={stats['cache_hit_rate']:.2%}"
)
