# Requirements

This file is the explicit capability and coverage contract for the project.

Use it to track what is actively in scope, what has been validated by completed work, what is intentionally deferred, and what is explicitly out of scope.

Guidelines:
- Keep requirements capability-oriented, not a giant feature wishlist.
- Requirements should be atomic, testable, and stated in plain language.
- Every **Active** requirement should be mapped to a slice, deferred, blocked with reason, or moved out of scope.
- Each requirement should have one accountable primary owner and may have supporting slices.
- Research may suggest requirements, but research does not silently make them binding.
- Validation means the requirement was actually proven by completed work and verification, not just discussed.

## Active

### R001 — Tek bakışta çalışma durumu görünürlüğü
- Class: primary-user-loop
- Status: active
- Description: Kullanıcı GSD açıldığında aktif milestone/slice/task, blocker ve sıradaki eylemi tek görünümde görmelidir.
- Why it matters: Oturum başlangıcında yön kaybını engeller ve yanlış işe başlanmasını azaltır.
- Source: user
- Primary owning slice: M001/S01
- Supporting slices: M001/S02
- Validation: mapped
- Notes: Görünüm sadece bilgi sunmamalı; net next action üretmelidir.

### R002 — Oturumlar arası bağlam hatırlama
- Class: continuity
- Status: active
- Description: Sistem commit geçmişi, `progress.md` ve `.gsd` durum dosyalarını birlikte okuyarak doğru devam noktasını belirlemelidir.
- Why it matters: Her seferinde geçmişin elle hatırlanması ihtiyacını ortadan kaldırır.
- Source: user
- Primary owning slice: M001/S02
- Supporting slices: M001/S01, M001/S05
- Validation: mapped
- Notes: Tutarsız kaynaklarda güvenli fallback davranışı gerekir.

### R003 — Düşük riskli otomatik iyileştirme akışı
- Class: quality-attribute
- Status: active
- Description: Test, log iyileştirmesi ve küçük refactor gibi düşük riskli değişiklikler otomatik seçilip uygulanabilmelidir.
- Why it matters: Geliştirme hızını artırır, manuel tekrarı azaltır.
- Source: user
- Primary owning slice: M001/S03
- Supporting slices: M001/S05
- Validation: mapped
- Notes: Kapsam dışı davranış değişikliği üretmemelidir.

### R004 — Commit öncesi zorunlu kullanıcı son onayı
- Class: compliance/security
- Status: active
- Description: Davranış etkileyen veya kalıcı değişiklik üreten commit işlemleri kullanıcı onayı olmadan yapılmamalıdır.
- Why it matters: Nihai kontrol kullanıcıda kalır, istenmeyen değişikliklerin riski düşer.
- Source: user
- Primary owning slice: M001/S04
- Supporting slices: M001/S03
- Validation: mapped
- Notes: Onay adımı mekanik ve atlanamaz olmalıdır.

### R005 — Genişleme taleplerini bozmadan sisteme ekleyebilme
- Class: operability
- Status: active
- Description: Sonradan gelen geliştirmeler requirement/slice düzeyinde eklenip mevcut planı bozmadan sıraya alınabilmelidir.
- Why it matters: Sistem tek seferlik plan yerine yaşayan bir çalışma çerçevesi olmalıdır.
- Source: user
- Primary owning slice: M001/S05
- Supporting slices: M001/S02, M001/S03
- Validation: mapped
- Notes: Deferred/Out-of-scope sınırları net tutulmalıdır.

## Validated

<!-- Henüz doğrulanmış requirement yok; doğrulamalar slice tamamlandıkça taşınacak. -->

## Deferred

### R020 — Çoklu kullanıcı / rol bazlı onay akışı
- Class: admin/support
- Status: deferred
- Description: Birden fazla onaylayıcı veya rol-temelli yetki akışları.
- Why it matters: Takım ölçeğinde gerekebilir.
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Tek kullanıcı odaklı ilk sürüm tamamlandıktan sonra değerlendirilecek.

### R021 — Gelişmiş otomatik risk skorlama
- Class: quality-attribute
- Status: deferred
- Description: Otomatik iyileştirmelerde kapsam, etki ve geri dönüş riski için puanlama.
- Why it matters: Otomasyon güvenini artırır.
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: İlk sürümde kural tabanlı düşük risk sınırı yeterli.

## Out of Scope

### R030 — Kullanıcı onayı olmadan davranış etkileyen otomatik commit
- Class: anti-feature
- Status: out-of-scope
- Description: Davranış değişikliği yapan commitlerin otomatik atılması.
- Why it matters: Kontrol kaybını ve istenmeyen regressions riskini artırır.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Açık kullanıcı talebi ile hariç tutuldu.

### R031 — Harici sistemlerde onaysız state değiştirme
- Class: constraint
- Status: out-of-scope
- Description: GitHub vb. dış servislerde kullanıcı onayı olmadan yazma işlemleri.
- Why it matters: Operasyonel güvenlik ve yönetişim için sınır koyar.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Read-only işlemler kapsam dışı değildir; yazma işlemleri onay ister.

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | primary-user-loop | active | M001/S01 | M001/S02 | mapped |
| R002 | continuity | active | M001/S02 | M001/S01, M001/S05 | mapped |
| R003 | quality-attribute | active | M001/S03 | M001/S05 | mapped |
| R004 | compliance/security | active | M001/S04 | M001/S03 | mapped |
| R005 | operability | active | M001/S05 | M001/S02, M001/S03 | mapped |
| R020 | admin/support | deferred | none | none | unmapped |
| R021 | quality-attribute | deferred | none | none | unmapped |
| R030 | anti-feature | out-of-scope | none | none | n/a |
| R031 | constraint | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 5
- Mapped to slices: 5
- Validated: 0
- Unmapped active requirements: 0
