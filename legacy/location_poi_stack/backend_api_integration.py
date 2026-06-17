"""
backend_api_integration.py - Yardimci POI entegrasyon modulu.

Bu dosya, ana `backend/app.py` akisina otomatik bagli degildir.
Rol: yardimci import/normalizasyon ve NLP sonucunu POI listesiyle birlestirme.
"""

import json
import csv
from typing import Dict, List, Optional, Any
from pathlib import Path

# Bu modul tasarim geregi yardimci moddur; ana backend route akisi bunu otomatik mount etmez.
INTEGRATION_MODE = "helper_only"

# =============================================================================
# POI VERİTABANI (Kullanıcıdan gelecek veriler)
# =============================================================================

class POIDatabase:
    """POI Veritabanı - Kullanıcıdan gelecek verilerle güncellenir."""
    
    def __init__(self):
        self.pois: Dict[str, List[Dict]] = {}
        self.poi_count = 0
    
    def load_from_csv(self, filepath: str) -> int:
        """CSV dosyasından POI verilerini yükler."""
        
        if not Path(filepath).exists():
            print(f"[POI DB] Dosya bulunamadı: {filepath}")
            return 0
        
        count = 0
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    ilce = row.get("ilçe", row.get("district", "")).lower().strip()
                    if not ilce:
                        continue
                    
                    # Normalize ilçe ismi
                    ilce_norm = ilce.replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")
                    
                    poi = {
                        "name": row.get("name", row.get("isim", "")),
                        "lat": float(row.get("lat", 0)) or None,
                        "lon": float(row.get("lon", 0)) or None,
                        "type": row.get("type", row.get("tür", row.get("poi_type", "cafe"))),
                        "address": row.get("address", row.get("adres", "")),
                        "phone": row.get("phone", row.get("telefon", "")),
                        "rating": float(row.get("rating", row.get("puan", 0)) or 0),
                        "tags": row.get("tags", "").split(",") if row.get("tags") else [],
                    }
                    
                    if ilce_norm not in self.pois:
                        self.pois[ilce_norm] = []
                    
                    self.pois[ilce_norm].append(poi)
                    count += 1
        
        except Exception as e:
            print(f"[POI DB] CSV okuma hatası: {e}")
        
        self.poi_count = count
        print(f"[POI DB] {count} POI yüklendi ({len(self.pois)} ilçe)")
        return count
    
    def load_from_json(self, filepath: str) -> int:
        """JSON dosyasından POI verilerini yükler."""
        
        if not Path(filepath).exists():
            print(f"[POI DB] Dosya bulunamadı: {filepath}")
            return 0
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            count = 0
            for ilce, pois in data.items():
                # İlçe ismini normalize et
                ilce_input = ilce.lower()
                ilce_norm = ilce_input.replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")
                
                # Eğer ilçe yoksa ekle, varsa birleştirme
                if ilce_norm not in self.pois:
                    self.pois[ilce_norm] = []
                
                for poi in pois:
                    if isinstance(poi, dict) and poi.get("name"):
                        # Tekrar kontrolü
                        existing_names = [p.get("name") for p in self.pois[ilce_norm]]
                        if poi.get("name") not in existing_names:
                            self.pois[ilce_norm].append(poi)
                            count += 1
            
            self.poi_count = count
            print(f"[POI DB] {count} POI yüklendi ({len(self.pois)} ilçe)")
            return count
        
        except Exception as e:
            print(f"[POI DB] JSON okuma hatası: {e}")
            return 0
    
    def search(self, ilce: str, poi_type: str = None, limit: int = 20) -> List[Dict]:
        """İlçede POI ara."""
        
        ilce_norm = ilce.replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")
        
        pois = self.pois.get(ilce_norm, [])
        
        # POI tipi ile filtrele (hem direkt hem alias eşleşmesi)
        if poi_type:
            # POI type alias'ları
            poi_aliases = {
                "kafe": ["cafe", "café", "coffee", "kahve"],
                "restaurant": ["restaurant", "restoran", "lokanta", "yemek"],
                "bar": ["bar", "pub", "gece"],
            }
            
            # Eşleşen tipler
            match_types = [poi_type]
            if poi_type in poi_aliases:
                match_types.extend(poi_aliases[poi_type])
            
            # Filtrele
            filtered = []
            for p in pois:
                ptype = p.get("type", "").lower()
                if any(mt in ptype for mt in match_types):
                    filtered.append(p)
            pois = filtered
        
        return pois[:limit]
    
    def search_all(self, poi_type: str = None, limit: int = 50) -> List[Dict]:
        """Tüm ilçelerde POI ara (lokasyon belirtilmediyse)."""
        
        all_pois = []
        
        for ilce, pois in self.pois.items():
            for poi in pois:
                if poi_type is None or poi_type in poi.get("type", "").lower():
                    poi_copy = poi.copy()
                    poi_copy["ilçe"] = ilce
                    all_pois.append(poi_copy)
        
        return all_pois[:limit]
    
    def get_stats(self) -> Dict:
        """Veritabanı istatistikleri."""
        return {
            "toplam_poi": self.poi_count,
            "toplam_ilçe": len(self.pois),
            "ilçeler": list(self.pois.keys())
        }


# =============================================================================
# BACKEND API ENTEGRASYON
# =============================================================================

class BackendNLPIntegration:
    """
    Standalone yardimci entegrasyon sinifi.

    Not:
    - Varsayilan olarak kendi basina calisir.
    - Ana backend'e route olarak otomatik mount edilmez.
    """
    
    def __init__(self, backend_url: str = "http://localhost:5000"):
        self.backend_url = backend_url
        self.poi_db = POIDatabase()
    
    def load_poi_data(self, filepath: str):
        """POI verilerini yükle."""
        if filepath.endswith(".csv"):
            return self.poi_db.load_from_csv(filepath)
        elif filepath.endswith(".json"):
            return self.poi_db.load_from_json(filepath)
        else:
            print(f"[Backend] Desteklenmeyen format: {filepath}")
            return 0
    
    def parse_query(self, query: str, bert_engine) -> Dict:
        """
        Sorguyu çözümler ve backend'e uygun formatta döndürür.
        
        Args:
            query: "Kadıköyde kafe Beşiktaşta kasap"
            bert_engine: IstanbulBERTEngine instance
        
        Returns:
            Backend'e gönderilecek format
        """
        # BERT ile parse et
        result = bert_engine.parse(query)
        
        if not result["success"]:
            return {"success": False, "error": result.get("error")}
        
        # Backend yanıtı oluştur
        response = {
            "success": True,
            "query": query,
            "segment_count": result["segment_count"],
            "segments": [],
            "total_poi_results": 0
        }
        
        for seg in result["segments"]:
            loc = seg.get("location")
            poi = seg.get("poi")
            osm_tags = seg.get("osm_tags", {})
            
            # POI ara
            if loc:
                pois = self.poi_db.search(loc, poi, limit=10)
            else:
                pois = self.poi_db.search_all(poi, limit=10)
            
            # Segment yanıtı
            segment_data = {
                "location": loc or "Tüm İstanbul",
                "poi_type": poi,
                "osm_tags": {k: v for k, v in osm_tags.items() if k != "aliases"},
                "poi_results": pois,
                "result_count": len(pois),
                "is_plural_normalized": seg.get("is_plural_normalized", False)
            }
            
            response["segments"].append(segment_data)
            response["total_poi_results"] += len(pois)
        
        return response
    
    def get_api_spec(self) -> Dict:
        """API spesifikasyonu."""
        return {
            "endpoints": {
                "/api/nlp/parse": {
                    "method": "POST",
                    "body": {"query": "string"},
                    "response": {
                        "success": "boolean",
                        "segments": "array",
                        "total_poi_results": "integer"
                    }
                },
                "/api/poi/search": {
                    "method": "POST",
                    "body": {"location": "string", "poi_type": "string"},
                    "response": {"results": "array"}
                }
            },
            "poi_db_stats": self.poi_db.get_stats()
        }


# =============================================================================
# VERİ ŞABLONU (Kullanıcıya Verilecek)
# =============================================================================

def create_sample_csv():
    """Örnek CSV şablonu oluştur."""
    
    sample_data = """ilçe,name,lat,lon,type,address,phone,rating
kadıköy,Starbucks Moda,40.9912,29.0265,cafe,Moda Cd. No:15,-,4.2
kadıköy,MMM Mantı,40.9905,29.0258,restaurant,Caferağa Mah.,-,4.5
kadıköy,Çeşm-i Cedit Cafe,40.9920,29.0275,cafe,Rasimpaşa Sk.,-,4.0
beşiktaş,Kahve Dünyası,41.0442,29.0101,cafe,Akaretler No:8,-,4.1
beşiktaş,İstanbul Pub,41.0438,29.0095,bar,Barbaros Bulv.,-,3.8
beşiktaş,Sultanahmet Köftecisi,41.0450,29.0110,restaurant,Ertuğrul Sk.,-,4.3
üsküdar,Çengelköy Kahvesi,41.0265,29.0432,cafe,Çengelköy Cd.,-,4.4
üsküdar,Pideci Hasan,41.0270,29.0440,restaurant,Çengelköy Mah.,-,4.2
şişli,Neşe Dürüm,41.0505,28.9860,restaurant,Halaskargazi Cd.,-,4.0
şişli,Glutensiz Cafe,41.0510,28.9855,cafe,İnönü Cd.,-,4.1
fatih,Süleymaniye Kahvesi,41.0167,28.9612,cafe,Süleymaniye Mah.,-,4.3
fatih,Kuru Fasulye Ali,41.0155,28.9620,restaurant,Langa Cd.,-,4.6
"""

    with open("poi_data_sample.csv", "w", encoding="utf-8") as f:
        f.write(sample_data)
    
    print("[Şablon] poi_data_sample.csv oluşturuldu")


def create_sample_json():
    """Örnek JSON şablonu oluştur."""
    
    sample_data = {
        "kadikoy": [
            {"name": "Starbucks Moda", "lat": 40.9912, "lon": 29.0265, "type": "cafe", "address": "Moda Cd. No:15", "rating": 4.2},
            {"name": "MMM Mantı", "lat": 40.9905, "lon": 29.0258, "type": "restaurant", "address": "Caferağa Mah.", "rating": 4.5},
        ],
        "besiktas": [
            {"name": "Kahve Dünyası", "lat": 41.0442, "lon": 29.0101, "type": "cafe", "address": "Akaretler No:8", "rating": 4.1},
            {"name": "İstanbul Pub", "lat": 41.0438, "lon": 29.0095, "type": "bar", "address": "Barbaros Bulv.", "rating": 3.8},
        ],
        "uskudar": [
            {"name": "Çengelköy Kahvesi", "lat": 41.0265, "lon": 29.0432, "type": "cafe", "address": "Çengelköy Cd.", "rating": 4.4},
        ],
    }
    
    with open("poi_data_sample.json", "w", encoding="utf-8") as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)
    
    print("[Şablon] poi_data_sample.json oluşturuldu")


# =============================================================================
# TEST
# =============================================================================

def test_full_integration():
    """Tam entegrasyon testi."""
    from bert_istanbul_integration import IstanbulBERTEngine
    
    print("=" * 60)
    print("BACKEND ENTEGRASYON TEST")
    print("=" * 60)
    
    # BERT Engine
    bert = IstanbulBERTEngine()
    
    # Backend Integration
    backend = BackendNLPIntegration()
    
    # Şablon oluştur ve otomatik yükle
    create_sample_csv()
    create_sample_json()
    
    print("\n[1] Şablonlar oluşturuldu, otomatik yükleniyor...")
    
    # Şablonları otomatik yükle
    csv_count = backend.load_poi_data("poi_data_sample.csv")
    json_count = backend.load_poi_data("poi_data_sample.json")
    
    print(f"\n[2] Toplam POI: {backend.poi_db.poi_count}")
    print(f"[3] İlçeler: {backend.poi_db.get_stats()['ilçeler']}")
    
    # Test sorguları
    test_queries = [
        "Kadıköyde kafe",
        "Beşiktaşta bar",
        "üsküdarda cafe",
        "kafeler",
    ]
    
    print("\n" + "=" * 60)
    print("SORGULAR")
    print("="*60)
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"SORGU: {query}")
        print("="*50)
        
        result = backend.parse_query(query, bert)
        
        if result["success"]:
            print(f"✅ {result['segment_count']} segment, {result['total_poi_results']} POI")
            
            for i, seg in enumerate(result["segments"]):
                loc = seg["location"]
                poi = seg["poi_type"]
                count = seg["result_count"]
                
                print(f"\n  Segment {i+1}: {loc} - {poi} ({count} sonuç)")
                
                if seg["poi_results"]:
                    for p in seg["poi_results"][:3]:
                        print(f"    📍 {p['name']} ({p.get('address', '')})")
                else:
                    print(f"    (Bu ilçede henüz POI yok)")
        else:
            print(f"❌ Hata: {result.get('error')}")
    
    print("\n" + "=" * 60)
    print("ŞABLON DOSYALAR")
    print("="*60)
    print("📄 poi_data_sample.csv - Excel formatında doldurun")
    print("📄 poi_data_sample.json - JSON formatında doldurun")
    print("\nKolonlar: ilçe, name, lat, lon, type, address, phone, rating")
    print("\nÖnemli: ilçe sütunu lowercase olmalı (örn: 'kadıköy', 'beşiktaş')")


if __name__ == "__main__":
    test_full_integration()

