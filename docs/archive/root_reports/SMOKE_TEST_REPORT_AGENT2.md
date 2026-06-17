# Smoke Test Report - Agent 2 (Negatif/Hata Akisi)

**Tarih:** 26.05.2026  
**Agent:** Agent 2 (Negatif/Hata Akisi)  
**Environment:** Windows 10, Python 3.13.6, Flask

---

## 1. Environment

| Bilesen | Deger |
|---------|-------|
| Python | 3.13.6 |
| Flask | Backend API |
| Test Port | 5002 |
| Backend PID | 17156 |

---

## 2. Startup Sonucu

| Adim | Sonuc |
|------|-------|
| Backend Baslatma | BASARILI |
| Health Check | `status == "ok"` (1 denemede) |

---

## 3. Negatif Test Sonuclari (N1-N8)

| Test | Endpoint | Body | Beklenen | Gercek | Durum |
|------|---------|------|----------|--------|-------|
| N1 | POST /api/nlp/parse | `{}` | 400, success=false, error_code=invalid_input | 400, success=false, error_code=invalid_input | **PASS** (artifact yenilendi) |
| N2 | POST /api/nlp/parse | `{"query":"   "}` | 400, success=false, error_code=invalid_input | 400, success=false, error_code=invalid_input | **PASS** |
| N3 | POST /api/nlp/parse | `not-json` (text/plain) | 400, success=false, error_code=invalid_input | 400, success=false, error_code=invalid_input | **PASS** |
| N4 | POST /api/nlp/parse | Bos body (application/json) | 400, success=false | 400, success=false | **PASS** |
| N5 | POST /api/poi/search | `{}` | 400, success=false, error_code=invalid_input | 400, success=false, error_code=invalid_input | **PASS** |
| N6 | POST /api/poi/search | limit="abc" | 400, success=false, error_code=invalid_input | 400, success=false, error_code=invalid_input | **PASS** |
| N7 | POST /api/poi/search | limit=0 | 400, success=false, error_code=invalid_input | 400, success=false, error_code=invalid_input | **PASS** |
| N8 | GET /api/unknown | - | 404 | 404 | **PASS** |

---

## 4. Hata Sozlesmesi Kontrol Sonucu

| Alan | Beklenen | Tüm Testlerde Dogru |
|------|----------|---------------------|
| `success` | false | Evet |
| `error_code` | "invalid_input" (N1-N7) | Evet |
| `error` | Mesaj string | Evet |

**Ek Kontroller:**
- NoneType .get() hatasi yok
- Tutarli JSON format (`success`, `error_code`, `error`)
- 400 yanitlari dogru formatta

---

## 5. Temizlik

| Islem | Sonuc |
|-------|-------|
| Process durdurma (PID 17156) | BASARILI |

---

## 6. OVERALL

**SONUC: PASS**

Tum negatif testler (N1-N8) basariyla gecti. Hata sozlesmesi tüm testlerde dogru sekilde uygulaniyor.

---

## 7. TestArtifacts

Test sonuclari: `smoke_artifacts/agent2/N1.json` - `N8.json`