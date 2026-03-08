# Komutlar Rehberi - GSD + SuperClaude + Claude Code

> Bu dosyada sık kullanılan komutların açıklamaları yer alır.

---

## 🚀 GSD (Get Shit Done) Komutları

### Proje Yönetimi
| Komut | Açıklama |
|-------|----------|
| `/gsd:new-project` | Yeni proje başlatır |
| `/gsd:progress` | İlerleme durumunu gösterir |
| `/gsd:resume-work` | **Gün başı** - Önceki oturumu özetler, görevleri devralır |
| `/gsd:pause-work` | **Gün sonu** - Oturumu kapatır, rapor hazırlar |

### Planlama ve Çalışma
| Komut | Açıklama |
|-------|----------|
| `/gsd:plan-phase` | Bir faz için detaylı plan oluşturur |
| `/gsd:execute-phase` | Plana göre çalışmayı yürütür |
| `/gsd:quick` | Hızlı bir görev yapar (kısa yol) |

### Görev Takibi
| Komut | Açıklama |
|-------|----------|
| `/gsd:add-todo` | Yeni bir todo ekler |
| `/gsd:check-todos` | Bekleyen todoları listeler |
| `/gsd:verify-work` | Yapılan işi doğrular (UAT) |

### Diğer
| Komut | Açıklama |
|-------|----------|
| `/gsd:help` | Tüm GSD komutlarını gösterir |
| `/gsd:settings` | GSD ayarlarını değiştirir |
| `/gsd:update` | GSD'yi günceller |

---

## 🤖 SuperClaude Komutları

### Kodlama ve Geliştirme
| Komut | Açıklama |
|-------|----------|
| `/sc:implement` | Yeni özellik veya kod implementasyonu |
| `/sc:design` | Mimari tasarım yapar |
| `/sc:build` | Projeyi derler/paketler |
| `/sc:test` | Testleri çalıştırır |

### Analiz ve Anlama
| Komut | Açıklama |
|-------|----------|
| `/sc:explain` | Kodu basitçe açıklar |
| `/sc:analyze` | Kalite, güvenlik, performans analizi |
| `/sc:index` | Proje dokümantasyonu oluşturur |
| `/sc:index-repo` | Repositoriyi indexler (token tasarrufu) |

### İyileştirme
| Komut | Açıklama |
|-------|----------|
| `/sc:improve` | Kod kalitesini iyileştirir |
| `/sc:cleanup` | Ölü kodu temizler |
| `/sc:refactor` | Kodu yeniden düzenler |

### Diğer
| Komut | Açıklama |
|-------|----------|
| `/sc:git` | Git işlemleri (commit, push, vb.) |
| `/sc:document` | Dokümantasyon yazdırır |
| `/sc:debug` | Hata ayıklama yapar |
| `/sc:research` | Konu hakkında araştırma yapar |
| `/sc:help` | Tüm SuperClaude komutlarını gösterir |

---

## 📝 Claude Code Yerel Komutları

| Komut | Açıklama |
|-------|----------|
| `/fast` | Hızlı modu aç/kapat |
| `/help` | Yardım göster |
| `/clear` | Sohbet geçmişini temizle |
| `/rename` | Oturumu yeniden adlandır |

---

## 💡 Kullanım Örnekleri

### Öğrenme Süreci İçin:
```
1. /sc:explain app.py
   → app.py dosyasını açıkla

2. /gsd:add-todo "Cache mekanizmasını anla"
   → Yeni görev ekle

3. /sc:analyze --security
   → Güvenlik analizi yap

4. /gsd:progress
   → İlerlemeyi kontrol et
```

### Kod Geliştirme İçin:
```
1. /gsd:plan-phase
   → Bir sonraki fazı planla

2. /sc:implement "POI arama özelliği"
   → Özelliği implement et

3. /sc:test
   → Testleri çalıştır

4. /gsd:verify-work
   → İşleri doğrula
```

---

## ⚡ Hızlı Başlangıç

**Her sabah:**
```bash
/gsd:resume-work
```

**Çalışırken bir şey anlamazsan:**
```bash
/sc:explain [kod veya dosya adı]
```

**Yeni bir fikir geldiğinde:**
```bash
/gsd:add-todo [fikir açıklaması]
```

**Gün sonunda:**
```bash
/gsd:pause-work
```
