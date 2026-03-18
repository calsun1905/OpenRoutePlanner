# CI ve Test Runbook

## Amaç
- API smoke testlerini ortamdan bağımsız çalıştırmak
- Temel syntax/regresyon kırılmalarını erken yakalamak

## Yerel Çalıştırma
```bash
python -m compileall backend scripts/tools
pytest -o addopts= tests/test_core/test_bert_nlp_preprocessing.py tests/test_core/test_intent_template_bundle.py tests/test_api/test_routes.py
```

## CI Akışı
- GitHub Actions dosyası: `.github/workflows/ci.yml`
- Her `push` ve `pull_request` için tetiklenir
- Aşamalar:
1. Bağımlılık kurulumu
2. Syntax smoke (`compileall`)
3. Odaklı test seti

## Commit Prensibi
- Tek commit = tek amaç
- Kod + test aynı committe olmalı
- Artifact dosyaları (`.coverage`, `*.db-wal`, `*.db-shm`, `_test_result.json`) commitlenmemeli
