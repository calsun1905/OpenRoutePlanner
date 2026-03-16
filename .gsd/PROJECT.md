# Project

## What This Is

RoutePlanner kod tabanında GSD metodolojisini operasyonel hale getiren planlama ve yürütme iskeleti. Amaç, oturumlar arasında bağlam kaybını azaltmak, tek bakışta mevcut durumu göstermek ve kontrollü otomasyon ile geliştirme akışını hızlandırmaktır.

## Core Value

Kullanıcının her oturumda nerede kalındığını tek bakışta görmesi ve bir sonraki doğru adımı güvenle başlatabilmesi.

## Current State

- RoutePlanner kod tabanı (Flask backend, test altyapısı, NLP/route/weather modülleri) mevcut.
- GSD tarafı yeni bootstrap ediliyor; henüz milestone/slice dokümantasyonu oluşturulmamış durumda.
- Commit kontrolü için son onay mercii kullanıcı olacak şekilde süreç kuralı belirlendi.

## Architecture / Key Patterns

- Planlama artefaktları `.gsd/` altında milestone → slice → task hiyerarşisi ile tutulur.
- Kaynak doğrular: roadmap checkbox durumları, slice planları, summary dosyaları.
- `STATE.md` hızlı gösterge olarak kullanılır; asıl kaynak dosyaların kendisidir.
- Düşük riskli otomasyon (test/log/küçük refactor) ile davranış etkileyen değişiklikler ayrıştırılır.

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [ ] M001: GSD Operasyonel Çekirdek — Tek bakış durum, oturum hafızası, kontrollü otomasyon ve commit onay kapısını çalışır hale getirir.
