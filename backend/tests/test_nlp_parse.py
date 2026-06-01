"""
NLP Parse Test - Yeni model + yeni threshold'larla
"""

import sys, os

sys.path.insert(0, os.path.dirname(__file__))

from bert_nlp_engine import get_bert_nlp_engine

engine = get_bert_nlp_engine()

print("=" * 70)
print("NLP PARSE TEST - Yeni Model + Yeni Threshold'lar")
print("=" * 70)

queries = [
    # Route sorgulari
    "Kadikoy'den Besiktas'a rota",
    "Taksim'den Uskudar'a nasil giderim",
    "Maltepe'den Kadikoy'e yol tarifi",
    "Levent'tan Besiktas'a gitmek istiyorum",
    "Sisli'den Bakirkoy'e rota planla",
    # POI sorgulari
    "Kadikoy'de kafe var mi",
    "Maltepe'de restoran ariyorum",
    "Besiktas'ta cami nerede",
    "Taksim'de park var mi",
    "Eminonu'nde eczane bul",
    # Single (tek hedef)
    "Taksim'e git",
    "Kadikoy'e nasil giderim",
    "Maltepe'ye gitmek istiyorum",
    # Multi (coklu)
    "Kadikoy, Taksim ve Besiktas'i gez",
    "Uc yer birden rota yap",
    # Chitchat (bilinmeyen)
    "Merhaba nasilsin",
    "Tesekkurler",
    "Iyi gunler",
    "Saat kac",
]

for query in queries:
    result = engine.parse(query, include_trace=False)
    qtype = result.get("type", "?")
    conf = result.get("confidence", 0.0)
    origin = result.get("origin", "")
    dest = result.get("destination", "")
    location = result.get("location", "")
    locations = result.get("locations", [])
    places = [p["place"] for p in result.get("detected_places", [])]
    error = result.get("error", "")
    ptime = result.get("parse_time", 0.0)

    # Sonucu formatla
    detail = ""
    if origin and dest:
        detail = f"{origin} -> {dest}"
    elif location:
        detail = f"konum: {location}"
    elif locations:
        detail = f"yerler: {locations}"
    elif error:
        detail = f"hata: {error}"

    print(f"  [{qtype:>8}] conf={conf:.2f}  time={ptime:.3f}s  '{query}'")
    if detail:
        print(f"           {detail}")
    if places:
        print(f"           tespit: {places}")
    print()
