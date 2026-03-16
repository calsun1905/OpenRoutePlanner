# M001: GSD Operasyonel Çekirdek — Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

## Project Description

Mevcut RoutePlanner kod tabanında GSD metodolojisinin temel çalışma katmanı kurulacak. Kullanıcı her oturumda tek bakışta nerede kaldığını görecek, sistem önceki commitler ve `progress.md` üzerinden bağlamı hatırlayacak, düşük riskli iyileştirmeler otomatik uygulanabilecek ve commit öncesi son onay kapısı kullanıcıda olacak.

## Why This Milestone

Bağlam kaybı ve kontrolsüz hız arasında denge ihtiyacı var. Kullanıcı hızlı ilerlemek istiyor ama son karar noktalarının kendisinde kalmasını özellikle vurguluyor. Bu milestone hem görünürlük hem hafıza hem otomasyon hem de onay kontrolünü aynı çerçevede birleştirerek sonraki genişlemeler için güvenli temel sağlar.

## User-Visible Outcome

### When this milestone is complete, the user can:

- GSD açılışında tek bakışta mevcut konumu (milestone/slice/task), blocker’ları ve net sıradaki adımı görebilir.
- Yeni oturumda geçmiş commit + `progress.md` + GSD durumunu dikkate alan doğru devam önerisi alır ve commit öncesi son onayı kendisi verir.

### Entry point / environment

- Entry point: `/gsd` akışı ve `.gsd/*` artefaktları
- Environment: local dev
- Live dependencies involved: local git repository, proje dosya sistemi

## Completion Class

- Contract complete means: Requirement sahipliği, kapsam sınırları ve onay kapısı kuralları dokümante ve roadmap ile izlenebilir olmalı.
- Integration complete means: Durum görünürlüğü + bağlam hatırlama + otomasyon + commit onayı birlikte çalışır şekilde doğrulanmalı.
- Operational complete means: Oturum yeniden başlatıldığında doğru devam noktası güvenilir şekilde üretilebilmeli.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Kullanıcı yeni bir oturumda tek bakış ekranından doğru “next action” alıp kaldığı işten devam edebilir.
- Sistem düşük riskli bir iyileştirmeyi otomatik uygular, doğrular ve commit aşamasında kullanıcıdan son onay bekler.
- Commit onayı verilmeden kalıcı commit adımı ilerlemez.

## Risks and Unknowns

- Düşük risk tanımı belirsiz kalırsa otomasyon beklenmedik davranış değişikliği üretebilir — sınırların netleşmesi gerekir.
- Commit geçmişi + `progress.md` + state arasında tutarsızlık olursa yanlış devam noktası seçilebilir — uzlaşma/fallback kuralı gerekir.
- Çok büyük geçmişte özetleme hatası birikebilir — “recent relevance” öncelikleme stratejisi gerekir.

## Existing Codebase / Prior Art

- `OpenRoutePlanner/backend/app.py` — mevcut operasyonel akışların merkezi; davranış etkisini anlamak için referans.
- `OpenRoutePlanner/tests/` — doğrulama kültürü var; otomatik iyileştirmede güvenlik ağını destekler.
- `CLAUDE.md` — repo düzeyi çalışma ve iletişim kuralları.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R001 — tek bakış durum görünürlüğünü sağlar.
- R002 — oturumlar arası bağlam sürekliliğini sağlar.
- R003 — düşük riskli otomasyon hızını sağlar.
- R004 — commit öncesi son kontrolü kullanıcıya bırakır.
- R005 — genişlemelerin planlı ve sürdürülebilir eklenmesini sağlar.

## Scope

### In Scope

- Tek bakış durum gösterimi için gerekli GSD artefakt düzeni
- Bağlam hatırlama kaynakları ve karar sıralaması
- Düşük riskli otomatik iyileştirme çerçevesi
- Commit öncesi zorunlu kullanıcı onayı

### Out of Scope / Non-Goals

- Çoklu kullanıcı/çoklu onaylayıcı sistemi
- Harici servislerde onaysız yazma işlemleri
- Davranış etkileyen değişikliklerin onaysız otomatik commit edilmesi

## Technical Constraints

- Plan artefaktları `.gsd/` hiyerarşisi ve şablon formatları ile uyumlu olmalı.
- Requirement sahipliği slice seviyesinde izlenebilir olmalı.
- Commitler branch üzerinde, az ve anlamlı tutulmalı; son onay kullanıcıda.

## Integration Points

- Git geçmişi — önceki işleri anlamak ve devam noktası çıkarmak
- `progress.md` / GSD state dosyaları — mevcut ilerleme sinyali
- Test/verification komutları — otomatik iyileştirme güvenlik doğrulaması

## Open Questions

- Düşük risk sınıfının çizgisi tam olarak hangi değişiklik desenlerini içerecek? — İlk sürümde kural tabanlı başlayıp gözlemle netleştirilecek.
- Tutarsız bağlam kaynaklarında nihai öncelik sırası ne olacak? — Slice planında deterministik sıralama tanımlanacak.
