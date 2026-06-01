"""
Kapsamli Semantik Test - 40 Gercek Turkee Sorgu
"""

import sys, os

sys.path.insert(0, os.path.dirname(__file__))

from bert_engine import get_bert_engine

engine = get_bert_engine()

print("=" * 70)
print("KAPSAMLI SEMANTIK TEST - 40 Gercek Sorgu")
print("Model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
print("=" * 70)

# =========================================================================
# GRUP 1: YER ISMI ESLESTIRME (Ayni yer, farkli yazim)
# =========================================================================
print("\n" + "=" * 70)
print("GRUP 1: Yer Ismi Eslestirme (Ayni yer, farkli yazim) - 10 test")
print("=" * 70)
tests = [
    ("Kadikoy", "Kadikoy"),
    ("Kadikoy", "Kadiköy"),
    ("Besiktas", "Besiktas"),
    ("Besiktas", "Besiktas"),
    ("Taksim", "Taksim"),
    ("Uskudar", "Uskudar"),
    ("Maltepe", "Maltepe"),
    ("Sisli", "Sisli"),
    ("Mecidiyekoy", "Mecidiyeköy"),
    ("Bakirkoy", "Bakirköy"),
]
for a, b in tests:
    sim = engine.similarity(a, b)
    durum = "✅" if sim > 0.80 else "⚠️"
    print(f"  {durum} {sim:.4f}  '{a}' vs '{b}'")

# =========================================================================
# GRUP 2: FARKLI YERLER (Düsük olmali)
# =========================================================================
print("\n" + "=" * 70)
print("GRUP 2: Farkli Yer Isimleri (Düsük olmali) - 10 test")
print("=" * 70)
tests = [
    ("Kadiköy", "Besiktas"),
    ("Taksim", "Üsküdar"),
    ("Maltepe", "Sisli"),
    ("Levent", "Kadiköy"),
    ("Eminönü", "Bostanci"),
    ("Besiktas", "Kartal"),
    ("Ortaköy", "Moda"),
    ("Bebek", "Kozyatagi"),
    ("Fatih", "Pendik"),
    ("Sariyer", "Maltepe"),
]
for a, b in tests:
    sim = engine.similarity(a, b)
    durum = "✅" if sim < 0.70 else "⚠️ YÜKSEK"
    print(f"  {durum} {sim:.4f}  '{a}' vs '{b}'")

# =========================================================================
# GRUP 3: INTENT ANLAMA - Route vs POI vs Chitchat
# =========================================================================
print("\n" + "=" * 70)
print("GRUP 3: Intent Anlama (Route / POI / Chitchat ayrimi) - 10 test")
print("=" * 70)

route_template = "Kadiköy'den Besiktas'a rota"
poi_template = "Kadiköy'de neler var"

queries = [
    # Route sorgulari
    ("Kadiköy'den Besiktas'a nasil giderim", "route"),
    ("Taksim'den Üsküdar'a yol tarifi", "route"),
    ("Maltepe'den Kadiköy'e rota planla", "route"),
    ("Levent'tan Besiktas'a gitmek istiyorum", "route"),
    # POI sorgulari
    ("Kadiköy'de kafe var mi", "poi"),
    ("Maltepe'de restoran ariyorum", "poi"),
    ("Besiktas'ta cami nerede", "poi"),
    ("Taksim'de park var mi", "poi"),
    # Chitchat
    ("Merhaba nasilsin", "chitchat"),
    ("Teşekkür ederim iyi günler", "chitchat"),
]

for query, expected_type in queries:
    sim_route = engine.similarity(query, route_template)
    sim_poi = engine.similarity(query, poi_template)

    if sim_route > sim_poi and sim_route > 0.60:
        detected = "route"
    elif sim_poi > sim_route and sim_poi > 0.60:
        detected = "poi"
    else:
        detected = "chitchat"

    correct = "✅" if detected == expected_type else "❌"
    print(f"  {correct} {query}")
    print(
        f"       Route={sim_route:.2f}  POI={sim_poi:.2f}  → {detected} (beklenen: {expected_type})"
    )

# =========================================================================
# GRUP 4: POI / MEKAN ESLESTIRME
# =========================================================================
print("\n" + "=" * 70)
print("GRUP 4: POI / Mekan Eslestirme - 10 test")
print("=" * 70)
tests = [
    ("kafe", "kahve"),
    ("restoran", "lokanta"),
    ("hastane", "eczane"),
    ("müze", "sergi"),
    ("park", "bahce"),
    ("cami", "kilise"),
    ("otel", "hotel"),
    ("eczane", "hastane"),
    ("sinema", "tiyatro"),
    ("AVM", "alisveris merkezi"),
]
for a, b in tests:
    sim = engine.similarity(a, b)
    durum = "✅" if sim > 0.50 else "⚠️"
    print(f"  {durum} {sim:.4f}  '{a}' vs '{b}'")

# =========================================================================
# GENEL OZET
# =========================================================================
print("\n" + "=" * 70)
print("GENEL OZET")
print("=" * 70)
print(
    """
Beklentiler:
  Grup 1 (Ayni yer):     0.80+ olmali
  Grup 2 (Farkli yer):   0.70- olmali
  Grup 3 (Intent):        Dogru tip tespit edilmeli
  Grup 4 (POI eslesme):  0.50+ olmali (anlamca ilgili)
"""
)

from bert_engine import get_embedding_cache_stats

stats = get_embedding_cache_stats()
print(
    f"  Cache: hits={stats['cache_hits']}, misses={stats['cache_misses']}, size={stats['cache_size']}"
)
