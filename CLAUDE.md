# image-match — Claude Code Guide

## Project overview

Maintained fork of the `image-match` library (upstream unmaintained). Finds approximate image matches using a perceptual signature algorithm backed by Elasticsearch.

- **Python 3.12+**
- **Elasticsearch 7.x** (`[es7]` extra) or **8.x** (`[es8]` extra) — separate explicit driver classes, not runtime detection
- Core algorithm in `image_match/goldberg.py` — do not rewrite this file

## Architecture

```
image_match/
    goldberg.py                  # Core algorithm (ImageSignature). Treat as read-only.
    signature_database_base.py   # Abstract base (add_image, search_image logic)
    _es_base.py                  # Private ES base class (_SignatureESBase)
    elasticsearch_driver_es7.py  # SignatureES7 — ES 7.x client API (body=, nested doc_type)
    elasticsearch_driver_es8.py  # SignatureES8 — ES 8.x client API (query=, document=, flat structure)
    elasticsearch_driver.py      # Backward-compat re-export; SignatureES is a deprecated factory
tests/
    conftest.py                  # Session fixture: downloads test1.jpg, generates test2.jpg as 3° rotation
    test_goldberg.py
    test_elasticsearch_driver.py           # ES7 tests (uses SignatureES7 + deprecation warning test)
    test_elasticsearch_driver_es7.py       # ES7 driver tests
    test_elasticsearch_driver_metadata_as_nested.py  # ES7 nested metadata filter tests
    test_elasticsearch_driver_es8.py       # ES8 tests (Elasticsearch(['http://localhost:9200']))
```

## Key design decisions

- **ES7 vs ES8 split is intentional** — ES7 kept for backward compat with existing apps; do not merge the drivers
- **`_SignatureESBase`** shares `delete_duplicates` and `_format_results`; abstract methods `_get_doc_source` and `_search_by_path` handle the API differences
- **`SignatureES`** in `elasticsearch_driver.py` is a deprecated factory function (not a class), emits `DeprecationWarning`, delegates to `SignatureES7`
- **Type hints on public API only** — internal helpers are unannotated

## Running tests locally

Requires Docker and a `.venv` with dependencies installed.

```bash
# Set up
python -m venv .venv && source .venv/bin/activate

make test-es7   # installs [es7,test], spins up ES 7.17.15, runs tests, tears down
make test-es8   # installs [es8,test], spins up ES 8.13.0, runs tests, tears down
make test       # both in sequence
make test-unit  # goldberg tests only (no Docker needed)
make lint       # ruff check .
```

## Known gotchas

- **`preprocess_image`** in `goldberg.py` — the `search_image → make_record → generate_signature` chain calls it twice. If the first pass returns a 2D (grayscale) ndarray, the second call must return it as-is (not pass to `rgb2gray`). This is handled at line ~257 in `goldberg.py`.
- **ES8 client** requires explicit hosts: `Elasticsearch(['http://localhost:9200'])`. `Elasticsearch()` without args raises `ValueError` in the v8 client.
- **Test images**: `test1.jpg` fetched from picsum.photos, `test2.jpg` is a 3° rotation of `test1.jpg` (~0.28 distance). This keeps the pair within the default distance cutoff (0.45) but above the tight cutoff (0.01) used in `test_lookup_with_cutoff`. Do not replace `test2.jpg` with an unrelated image — distances will exceed the cutoff and filter tests will fail.
- **Module-level network calls break pytest collection** — all downloads must be in session-scoped fixtures, never at module scope.
- **ES 7.17.0 crashes on modern Linux** (cgroupv2 JDK bug) — CI uses 7.17.15+.

## Linting

`ruff` is the linter. Run before committing:
```bash
.venv/bin/ruff check .
.venv/bin/ruff check . --fix   # auto-fix import ordering etc.
```

Import order: stdlib → third-party → local (`image_match.*`, `tests.*`).

## Adding a dependency

Edit `pyproject.toml`. Core deps go in `[project].dependencies`. ES-version-specific deps go in `[project.optional-dependencies]`.
