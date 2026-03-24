# Cache ve repoda tutulacak dosyalar — politika

Amaç: **hangi verinin nerede üretildiğini** ve **Git’e neyin bilinçli konduğunu** net tutmak.

## 1. Çalışma anında oluşan (genelde repoda tutulmaz)

| Yol | Açıklama |
|-----|----------|
| `backend/data/app_data.db` | Kullanıcı rotaları / kayıtlı konumlar. Makineye özel. |
| `backend/data/app_data.db-wal`, `-shm` | SQLite WAL yardımcı dosyaları. |
| `backend/data/pois.db` | POI önbelleği; TTL ile yenilenir. |
| `backend/data/*.graphml` | OSM yürüyüş grafiği önbelleği (`.gitignore` içinde). |

Bu dosyalar **runtime** üretilir; yedekleme gerekiyorsa ayrıca kopyalanmalıdır.

## 2. İsteğe bağlı repoda (ekip / çoklu PC senkronu)

Bazı projelerde `backend/cache/geocodes.db` ve `backend/cache/*.json` **bilinçli olarak** repoya alınabilir; amaç: ilk açılışta aynı ortama yakın davranış.

**Dikkat:** `.gitignore` içinde `backend/cache/` kuralları bu dosyaların takibini **engelleyebilir**. Repoda tutmak istiyorsanız:

- `git check-ignore -v backend/cache/geocodes.db` ile hangi kuralın eşleştiğini kontrol edin.
- Gerekirse `!backend/cache/geocodes.db` gibi **istisna** satırları ekleyin.

## 3. POI sonuç önbelleği — tazelik (kod)

`backend/route_config.py` içinde:

- **`POI_CACHE_SOFT_TTL_DAYS`** (varsayılan **14**): Yaklaşık iki haftalık “tazelik” penceresi; bu süre içinde cache hit → “güncel” sayılır.
- **`POI_CACHE_HARD_TTL_DAYS`** (varsayılan **30**): Bu süreden sonra canlı sorgu zorunlu (veya stale-while-revalidate akışı).
- **`POI_CACHE_EMPTY_TTL_HOURS`**: Boş sonuçlar daha kısa tutulur (yeni açılan mekanlar için).

- **`pois_archive` tablosu** (`pois.db` içinde): Ana `pois` satırı güncellenmeden önce eski JSON + zaman damgası buraya kopyalanır; `POI_ARCHIVE_MAX_PER_KEY` (varsayılan 5) ile yer başına son N sürüm tutulur. İleride API veya manuel geri yükleme için kullanılabilir.

Özet: **Yaklaşık iki haftalık yumuşak pencere** + **eski sürümler silinmeden önce arşivde**.

## 4. Geçici / yedek HTML

`index.before-encoding-fix.backup.html` gibi dosyalar **geçici** kabul edilir; kalıcı çözüm `index.html` + `app.js` içindedir.  
Bu tür yedekler repoda tutulmayabilir veya `docs/archive/` altına taşınabilir.
