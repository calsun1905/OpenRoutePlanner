---
description: Projeyi her seferinde nasıl başlatırsın?
---

Bu projeyi her açtığında şu adımları izleyerek hızlıca çalıştırabilirsin:

### 1. Terminali Aç ve Doğru Klasöre Git
VS Code terminalinde (veya PowerShell'de) ana dizinde olduğunu kontrol et.

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
