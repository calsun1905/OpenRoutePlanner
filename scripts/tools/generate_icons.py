import sys
import os
import json

# Script scripts/tools/ içinde; backend OpenRoutePlanner/backend'de
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.normpath(os.path.join(_script_dir, '..', '..'))
sys.path.insert(0, os.path.join(_project_root, 'backend'))

from osm_poi_dictionary import POI_MAPPING

unique_tags = {}
for keyword, tags in POI_MAPPING.items():
    tag_str = str(tags)
    if tag_str not in unique_tags:
        unique_tags[tag_str] = keyword

print(f"Total unique OSM tags: {len(unique_tags)}")

default_emoji = "📍"
emojis = {
    "kafe": "☕", "restoran": "🍽️", "bar": "🍻", "dondurmacı": "🍦", "market": "🛒", 
    "bakkal": "🏪", "tekel": "🍾", "fırın": "🥖", "kasap": "🥩", "manav": "🍎", 
    "giyim": "👕", "ayakkabıcı": "👞", "kozmetik": "💄", "kuyumcu": "💍", "saatçi": "⌚", 
    "çiçekçi": "💐", "kitapçı": "📚", "kırtasiye": "✏️", "oyuncakçı": "🧸", "elektronik": "💻", 
    "telefoncu": "📱", "mobilya": "🛋️", "avm": "🛍️", "eczane": "💊", "pet shop": "🐾", 
    "bisikletçi": "🚲", "nalbur": "🛠️", "kuru temizleme": "👔", "terzi": "🧵", "kuaför": "✂️",
    "hastane": "🏥", "klinik": "🩺", "dişçi": "🦷", "veteriner": "🐕", "kan merkezi": "🩸",
    "banka": "🏦", "atm": "🏧", "döviz": "💱", "postane": "🏣", "benzinlik": "⛽", 
    "şarj": "🔌", "polis": "🚓", "itfaiye": "🚒", "belediye": "🏛️", "adliye": "⚖️", 
    "tuvalet": "🚻", "duş": "🚿", "çeşme": "🚰", "çöp kutusu": "🗑️", "müze": "🏛️", 
    "sanat galerisi": "🖼️", "otel": "🏨", "pansiyon": "🛏️", "kamp": "⛺", "hayvanat bahçesi": "🦁", 
    "tema park": "🎢", "akvaryum": "🐟", "manzara": "🌄", "park": "🌳", "oyun parkı": "🎠", 
    "doğa": "🏞️", "stadyum": "⚽", "spor salonu": "🏋️", "yüzme havuzu": "🏊", "plaj": "🏖️", 
    "orman": "🌲", "piknik": "🍱", "sinema": "🎬", "tiyatro": "🎭", "gece kulübü": "🪩", 
    "casino": "🎰", "tarihi yer": "🏺", "kale": "🏰", "anıt": "🗽", "cami": "🕌", 
    "kilise": "⛪", "sinagog": "🕍", "mezarlık": "🪦", "okul": "🏫", "üniversite": "🎓", 
    "anaokulu": "🧸", "kütüphane": "📚", "sürücü kursu": "🚗", "durak": "🚏", 
    "metro": "🚇", "tren istasyonu": "🚉", "tramvay": "🚋", "havalimanı": "✈️", 
    "otogar": "🚌", "taksi durağı": "🚕", "vapur": "⛴️", "liman": "⚓", "otopark": "🅿️", 
    "şelale": "🌊", "göl": "🦆", "nehir": "🚣", "dağ": "⛰️", "mağara": "🦇"
}

html_buttons = []

for tag_str, keyword in unique_tags.items():
    emoji = emojis.get(keyword, default_emoji)
    tags_dict = json.dumps(eval(tag_str)).replace('"', '&quot;') # for data-tags attribute
    title = keyword.capitalize()
    btn = f'<button class="btn btn-poi btn-poi-dynamic" data-category="{keyword}" title="{title}">{emoji} {title}</button>'
    html_buttons.append(btn)

tmp_path = os.path.join(_project_root, 'tmp_buttons.html')
with open(tmp_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(html_buttons))
print(f"Generated {len(html_buttons)} buttons in tmp_buttons.html")
