# M001: GSD Operasyonel Çekirdek

**Vision:** Kullanıcıya tek bakışta güvenilir durum görünürlüğü sunan, oturumlar arası bağlamı doğru taşıyan, düşük riskli otomasyonu kontrollü çalışan ve commit final onayını kullanıcıda tutan GSD yürütme çekirdeği.

## Success Criteria

- Kullanıcı GSD açtığında aktif iş konumunu, blockerları ve net sonraki adımı tek görünümde görebilir.
- Yeni oturumda sistem commit geçmişi + `progress.md` + state sinyallerinden doğru devam önerisi üretir.
- Düşük riskli otomatik iyileştirme çalışır, doğrulama üretir ve commit öncesi kullanıcı onayı olmadan commit adımı ilerlemez.

## Key Risks / Unknowns

- Düşük risk sınırı yanlış tanımlanırsa otomasyon davranış değişikliği riski doğurur.
- Farklı bağlam kaynaklarında (commit/progress/state) çelişki olduğunda yanlış next-action seçimi olabilir.

## Proof Strategy

- Düşük risk sınırı belirsizliği → retire in S03 by proving yalnızca izinli değişiklik sınıfları otomatik uygulanır ve doğrulama izi bırakır.
- Bağlam çelişkisi riski → retire in S02 by proving kaynak öncelikleme/fallback ile deterministik devam kararı üretilir.

## Verification Classes

- Contract verification: Artifact kontrolleri + requirement mapping + plan dosya doğrulaması
- Integration verification: Git geçmişi + progress/state girdileri ile devam kararı üretiminin uçtan uca test edilmesi
- Operational verification: Oturum yeniden başlatma senaryosunda doğru next-action üretimi
- UAT / human verification: “tek bakışta netlik” ve onay kapısı deneyiminin kullanıcı tarafından doğrulanması

## Milestone Definition of Done

This milestone is complete only when all are true:

- Tüm slice deliverable’ları tamamlanmış ve roadmap/slice artefaktlarına işlenmiş olur.
- Durum görünürlüğü, bağlam hatırlama, otomatik iyileştirme ve commit onay kapısı birlikte wired çalışır.
- Gerçek giriş noktası (`/gsd` + `.gsd` artefakt akışı) üzerinden akış yürütülüp doğrulanır.
- Success criteria canlı davranış ve doğrulama kanıtlarıyla tekrar kontrol edilir.
- Final integrated acceptance senaryoları geçer.

## Requirement Coverage

- Covers: R001, R002, R003, R004, R005
- Partially covers: none
- Leaves for later: R020, R021
- Orphan risks: none

## Slices

- [ ] **S01: Durum Panosu ve Tek Bakış Akışı** `risk:medium` `depends:[]`
  > After this: Kullanıcı aktif milestone/slice/task, blocker ve next-action bilgisini tek bakışta görebilir.

- [ ] **S02: Oturum Hafızası ve Devam Kararı** `risk:high` `depends:[S01]`
  > After this: Yeni oturumda commit geçmişi + progress/state sinyallerinden deterministik devam önerisi üretilebilir.

- [ ] **S03: Düşük Riskli Otomatik İyileştirme Motoru** `risk:medium` `depends:[S02]`
  > After this: Düşük riskli değişiklikler otomatik seçilip uygulanır ve doğrulama çıktısı üretir.

- [ ] **S04: Commit Onay Kapısı (Final Yetki Kullanıcıda)** `risk:high` `depends:[S03]`
  > After this: Commit akışı zorunlu kullanıcı onayı olmadan tamamlanamaz.

- [ ] **S05: Genişleme Hazırlığı ve Sürdürülebilir Planlama** `risk:low` `depends:[S04]`
  > After this: Yeni talepler requirement/slice olarak sisteme bozmadan eklenip sıraya alınabilir.

## Boundary Map

### S01 → S02

Produces:
- `STATE.md` tek bakış alanları için sabit görünüm sözleşmesi: Active Milestone/Slice/Task, Blockers, Next Action
- Durum kaynak öncelik girdileri için temel alanlar

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- Bağlam toplama sözleşmesi: commit geçmişi özeti + `progress.md` özeti + `.gsd` durum özeti
- Deterministik “next action recommendation” çıktısı

Consumes from S01:
- `STATE.md` görünüm sözleşmesi ve alanları

### S03 → S04

Produces:
- Düşük riskli otomasyon için izinli değişiklik sınıfları
- Otomatik değişiklik sonrası zorunlu doğrulama çıktısı (pass/fail + evidence)

Consumes from S02:
- Deterministik devam önerisi

### S04 → S05

Produces:
- Commit öncesi zorunlu onay kapısı (user-confirmed flag olmadan commit yok)
- Commit öncesi özet çıktısı (ne değişecek, neden)

Consumes from S03:
- Otomatik iyileştirme çıktıları ve doğrulama kanıtı

### S05 → Future Milestones

Produces:
- Requirement güncelleme akışı (Active/Deferred/Out-of-scope geçiş kuralları)
- Yeni slice/milestone ekleme için sürdürülebilir planlama protokolü

Consumes from S04:
- Onay kontrollü commit modeli
