---
description: Proje oturumunu kayıt altına alıp sonlandırır ve ilgili hookları çalıştırır.
---

Bu komut her yapay zeka sohbet oturumunu kapattığında, o günkü tüm ilerlemeyi kaydetmek, progress'i güncellemek ve git commit'i hazırlamak için tasarlanmıştır.

### 1. Oturum Bitiş Hook'unu Çalıştır
```bash
# Agent, aşağıdaki dosyayı oku ve sadece Hızlı Kapanış (Lite Mod) adımlarını VEYA tüm adımları uygula.
# view_file('.claude/hooks/SessionEnd.claude')
```
*Not: AI (Agent) bu dosyayı okuyacak, tamamlanan/yarım kalan işlerini özetleyecek ve sana günün kapanış raporunu/commit mesajını sunacaktır.*

### 2. Geliştirme Sunucusunu Durdur
Kullanıcı onay verirse, açık olan backend/frontend process'lerini terminal üzerinden kapat.

### 3. Git Commit (Kullanıcı Onayına Bağlı)
Eğer 1. adımın sonunda kullanıcı onay verdiyse:
```bash
git add .
git commit -m "AI tarafından önerilen mesaj"
# git push origin main
```
