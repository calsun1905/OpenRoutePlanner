---
description: Proje oturumunu yönetilen biçimde başlatır ve ilgili hookları çalıştırır.
---

Bu komut her yeni bir yapay zeka sohbet oturumu açtığında, tüm geçmişi ve süreci hatırlayabilmemiz için tasarlanmıştır.

### 1. Oturum Başlangıç Hook'unu Çalıştır
```bash
# Agent, aşağıdaki dosyayı oku ve sadece Hızlı Başlangıç (Lite Mod) adımlarını VEYA tüm adımları uygula.
# view_file('.claude/hooks/SessionStart.claude')
```
*Not: AI (Agent) bu dosyayı okuyacak, statüleri kontrol edecek ve sana günün özetini/sorularını sunacaktır.*

### 2. Sanal Ortamı (Venv) Aktif Et
```powershell
.\venv\Scripts\activate
```
*Not: Satırın başında `(venv)` yazısını gördüğünde hazırsın.*

### 3. Backend'i Başlat
```powershell
cd OpenRoutePlanner/backend
python app.py
```

### 4. Tarayıcıda Aç
Sunucu çalıştıktan sonra `OpenRoutePlanner/frontend/index.html` dosyasını tarayıcınla (Chrome, Edge vb.) aç.

---
// turbo-all
// Bu adımları otomatik çalıştırmak istersen bana söyleyebilirsin.
