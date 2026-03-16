# OpenRoutePlanner - Önemli Komutlar

## 🚀 Uygulama Komutları

### Backend
```bash
# Sanal ortam aktifleştir
cd OpenRoutePlanner
.venv\Scripts\activate  # Windows

# Backend başlat
cd backend
python app.py
# Çalışır: http://localhost:5000

# Bağımlılık yükle
pip install -r requirements.txt
```

### Frontend
```bash
# Tarayıcıda aç
# file:///path/to/OpenRoutePlanner/frontend/index.html
# veya http://localhost:5000 (backend çalışıyorsa)
```

## 🔧 Geliştirme Komutları

### Python Test
```bash
# BERT test
cd backend
python test_bert_extraction.py

# Endpoint test
python test_endpoints.py

# Alternatif rota test
python test_alt_routes.py

# Motor test
python test_engine.py

# Timeline test
python test_timeline.py

# Quick test
python quick_test.py
```

### OSM İndirme
```bash
# İstanbul haritası indir
cd backend
python download_istanbul.py

# Genel harita indir
python download_maps.py
```

## 🛠️ Sistem Komutları (Windows)

### Dosya ve Klasör
```bash
# Listele
ls
ls -la  # detaylı

# Klasöre git
cd OpenRoutePlanner/backend

# Geri git
cd ..

# Ana dizine git
cd ~
```

### Arama
```bash
# Dosya ara
find . -name "*.py"

# İçerik ara (grep)
grep -r "TODO" backend/

# Case-insensitive arama
grep -ri "error" backend/
```

### Git
```bash
# Durum
git status

# Değişiklikleri göster
git diff

# Commit
git add .
git commit -m "mesaj"

# Push
git push

### Log
git log --oneline -10
```

## 📱 Proje Yönetimi Komutları

### GSD (Get Shit Done)
```bash
/gsd:resume-work      # Gün başı - oturumu özetle
/gsd:pause-work       # Gün sonu - rapor hazırla
/gsd:add-todo         # Yeni görev ekle
/gsd:check-todos      # Todoları kontrol et
/gsd:progress         # İlerleme göster
/gsd:plan-phase       # Faz planla
/gsd:execute-phase    # Plana göre çalış
/gsd:quick            # Hızlı görev
/gsd:verify-work      # İş doğrula (UAT)
```

### SuperClaude
```bash
/sc:implement         # Yeni özellik implement et
/sc:design            # Mimari tasarım
/sc:build             # Derle/paketle
/sc:test              # Test çalıştır
/sc:explain           # Kodu açıklarla
/sc:analyze           # Kalite/güvenlik/performans analizi
/sc:index             # Proje dokümantasyonu oluştur
/sc:index-repo        # Repoyi indexle (token tasarrufu)
/sc:improve           # Kod kalitesi iyileştir
/sc:cleanup           # Ölü kod temizle
/sc:git               # Git işlemleri
/sc:document          # Dokümantasyon yaz
/sc:debug             # Hata ayıklama
/sc:research          # Araştırma yap
```

### Claude Code
```bash
/fast        # Hızlı mod aç/kapat
/help        # Yardım göster
/clear       # Sohbet geçmişini temizle
/rename      # Oturumu yeniden adlandır
```

## 🗂️ Dosya Yolu Referansları

### Proje Kök
`c:\Users\Gaming\Desktop\projects\routeplanner`

### OpenRoutePlanner
`c:\Users\Gaming\Desktop\projects\routeplanner\OpenRoutePlanner`

### Backend
`c:\Users\Gaming\Desktop\projects\routeplanner\OpenRoutePlanner\backend`

### Frontend
`c:\Users\Gaming\Desktop\projects\routeplanner\OpenRoutePlanner\frontend`

## 📊 Log ve Debug

### Backend Log
`backend/backend_errors.log`

### Debug Dosyaları
- `debug_out.pkl` - Python pickle çıktısı
- `debug_queries.json` - Debug sorguları
- `test_out.txt` - Test çıktısı

## 🔍 İpuçları

1. **Hızlı başlangıç:** `cd OpenRoutePlanner/backend && python app.py`
2. **Progress takibi:** `OpenRoutePlanner/progress.md` dosyasını oku
3. **API endpointleri:** `OpenRoutePlanner/PROJECT_INDEX.md` dosyasında
4. **OSM rehberi:** `OpenRoutePlanner/OSM_API_REHBERI.md` dosyasında
