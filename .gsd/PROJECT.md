# Project

## What This Is

RoutePlanner kod tabanında GSD metodolojisini operasyonel hale getiren planlama ve yürütme iskeleti. Amaç, oturumlar arasında bağlam kaybını azaltmak, tek bakışta mevcut durumu göstermek ve kontrollü otomasyon ile geliştirme akışını hızlandırmaktır.

## Core Value

Kullanıcının her oturumda nerede kalındığını tek bakışta görmesi ve bir sonraki doğru adımı güvenle başlatabilmesi.

## Current State

- RoutePlanner kod tabanı (Flask backend, test altyapısı, NLP/route/weather modülleri) mevcut.
- GSD tarafı aktif olarak kullanılıyor; oturum içi çalışma ve lokal değişiklik yönetimi uygulanıyor.
- Commit onayı kuralı: bundan sonra asıl commit/push işlemlerinden önce kullanıcıya sorulacaktır.

## Recent Progress (özet)

Aşağıdaki değişiklikler yerel çalışma ağacına uygulandı ve kullanıcı isteği üzerine commitlendi (lokal, remote'a push edilmedi):

- tests/test_s01_state.py: merge çatışması çözüldü ve çözüm commitlendi (commit: ff47922).
- OpenRoutePlanner/backend/app.py: turn-by-turn adımlarının üretim mantığı güncellendi:
  - Türkçe talimat şablonları eklendi (deterministik varyasyonlar), roundabout (kavşak) tespiti, her adım için `step_id` ve `cumulative_distance_m` alanları eklendi.
- OpenRoutePlanner/backend/test_route_steps.py: yeni/mühendislik testleri eklendi (basic, missing_street_name, roundabout_detection).
- OpenRoutePlanner/frontend/index.html: navigasyon paneli ve konum modu seçici eklendi (map_center / gps).
- OpenRoutePlanner/frontend/js/app.js: TTS entegrasyonu, adım vurgulama, map-center simülasyonu ve gerçek GPS (navigator.geolocation) destekli otomatik ilerleme eklendi.
- .github/workflows/ci.yml: pytest çalıştıran basit GitHub Actions workflow dosyası eklendi.
- Git: değişiklikler iki adımda commitlendi:
  - OpenRoutePlanner içindeki dosyalar için tek bir commit (bddcbb8) eklendi.
  - Superproject'te submodule pointer'ı güncellenerek commit (21bbfc2) eklendi.

Not: Yukarıdaki commits yereldir; remote'a (origin) push edilmedi.

## Next steps (kısa)

- Kullanıcı onayına bağlı işlemler:
  - Remote'a push & PR açma (kullanıcının yazılı onayı gerekir).
  - Lokal test çalıştırma (pytest) — öncelikle virtualenv ve bağımlılık kurulumu gerekli.
  - Commit mesaj düzenleme veya squashtan sonra farklı bir geçmiş yeniden yazma isteği.

## Architecture / Key Patterns

- Planlama artefaktları `.gsd/` altında milestone → slice → task hiyerarşisi ile tutulur.
- Kaynak doğrular: roadmap checkbox durumları, slice planları, summary dosyaları.
- `STATE.md` hızlı gösterge olarak kullanılır; asıl kaynak dosyaların kendisidir.
- Düşük riskli otomasyon (test/log/küçük refactor) ile davranış etkileyen değişiklikler ayrıştırılır.

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [ ] M001: GSD Operasyonel Çekirdek — Tek bakış durum, oturum hafızası, kontrollü otomasyon ve commit onay kapısını çalışır hale getirir.
