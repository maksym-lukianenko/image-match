# image-match Modernization Design

**Date:** 2026-04-07
**Author:** Maksym Lukianenko
**Status:** Approved

## Overview

This document describes the modernization plan for the forked `image-match` library. The library is no longer maintained upstream. The goal is to bring it up to current Python and packaging standards while preserving the core image-matching algorithm and maintaining backward compatibility where practical.

## Goals

- Python 3.12+ only
- Remove Python 2 compatibility shims (`six`)
- Modern packaging (`pyproject.toml`)
- Elasticsearch 7.x and 8.x support via separate explicit driver classes
- Retire MongoDB driver
- Type hints on public API
- Replace Travis CI with GitHub Actions
- Clean, working test suite

## Non-Goals

- Rewriting the core algorithm (`goldberg.py`)
- Async support
- Supporting Elasticsearch 9.x (too early in ecosystem adoption)
- MongoDB support (retired)
- Strict `mypy` enforcement

---

## Phase 1: Packaging

### Changes

Replace `setup.py` + `pytest-runner` with `pyproject.toml` using `setuptools` as the build backend.

**`pyproject.toml` structure:**
- `[build-system]`: `setuptools>=68`, `wheel`
- `[project]`: name, version, description, `requires-python = ">=3.12"`, license, classifiers
- `[project.optional-dependencies]`:
  - `es7 = ["elasticsearch>=7.0.0,<8.0.0"]`
  - `es8 = ["elasticsearch>=8.0.0,<9.0.0"]`
  - `test = ["pytest", "pytest-cov", "ruff"]`
  - `dev = [includes test + ipython]`
- Core `dependencies`: `scikit-image>=0.19`, `numpy>=1.24`, `Pillow>=9.0`

**Notes:**
- `numpy` and `Pillow` were previously used but not declared as dependencies — this fixes that.
- `six` is removed entirely from all dependency lists.
- `cairosvg` optional extra is preserved as `extra = ["cairosvg>=2.0"]`.
- `pytest.ini` settings migrated to `[tool.pytest.ini_options]` in `pyproject.toml`.
- `ruff` replaces the `pep8` + `pyflakes` + `pylint` trio.

---

## Phase 2: Code Cleanup

### Remove `six`

`six` is used in `goldberg.py` for Python 2/3 string type compatibility. With Python 3.12 as the minimum, this is dead code.

**Replacements:**
- `from six import string_types, text_type` → removed
- `isinstance(x, string_types)` → `isinstance(x, str)`
- `isinstance(x, text_type)` → `isinstance(x, str)`
- `try/except` urlretrieve import in `tests/test_goldberg.py` → `from urllib.request import urlretrieve`
- `u''` unicode string literals in tests → plain `''` strings

### Python 3.12 Idioms

- Remove explicit `(object)` base class inheritance where present
- Replace `type(x) is int` → `isinstance(x, int)` in `signature_database_base.py` and `goldberg.py`

### Delete MongoDB Driver

- Remove `image_match/mongodb_driver.py`
- Remove `tests/test_mongodb_driver.py` (if present)
- No replacement or deprecation shim — full removal

---

## Phase 3: Elasticsearch Driver Split

### File Structure

```
image_match/
    _es_base.py                    # shared internal base (private, not public API)
    elasticsearch_driver.py        # backward-compat re-export of SignatureES7 + SignatureES8
    elasticsearch_driver_es7.py   # SignatureES7 — ES 7.x client API
    elasticsearch_driver_es8.py   # SignatureES8 — ES 8.x client API
```

### `_SignatureESBase` (private)

Inherits from `SignatureDatabaseBase`. Contains all ES-specific shared logic:
- `__init__` with shared parameters: `es`, `index`, `doc_type`, `timeout`, `size` — calls `super().__init__()` to chain into `SignatureDatabaseBase`
- `delete_duplicates`
- Shared response-formatting helpers used by both `search_single_record` implementations

`search_image` and `add_image` are inherited unchanged from `SignatureDatabaseBase`.

Abstract methods to be implemented by subclasses:
- `search_single_record`
- `insert_single_record`

### `SignatureES7`

Implements the ES 7.x client API:
- `es.search(index=..., body={...})` — `body=` kwarg
- `es.index(index=..., body={self.doc_type: rec})` — nested under doc_type
- `doc_type` field used as document namespace

### `SignatureES8`

Implements the ES 8.x client API:
- `es.search(index=..., query={...}, source_excludes=[...])` — no `body=`
- `es.index(index=..., document={...})` — `document=` replaces `body=`
- `doc_type` field still stored for schema consistency but not used for ES API calls

### Key API Differences

| Area | ES 7.x (`SignatureES7`) | ES 8.x (`SignatureES8`) |
|---|---|---|
| Search | `es.search(index=..., body={...})` | `es.search(index=..., query={...})` |
| Index | `es.index(index=..., body={doc_type: rec})` | `es.index(index=..., document={...})` |
| `doc_type` | Used as field namespace | Stored but not passed to ES API |
| Response format | Same | Same |

### Backward Compatibility

`elasticsearch_driver.py` re-exports:
```python
from image_match.elasticsearch_driver_es7 import SignatureES7
from image_match.elasticsearch_driver_es8 import SignatureES8

# Backward compat alias with deprecation warning
import warnings

def SignatureES(*args, **kwargs):
    warnings.warn(
        "SignatureES is deprecated. Use SignatureES7 or SignatureES8 explicitly.",
        DeprecationWarning,
        stacklevel=2,
    )
    return SignatureES7(*args, **kwargs)
```

---

## Phase 4: Type Hints on Public API

Annotations are added to public-facing methods only. Internal helpers remain unannotated.

### `goldberg.py` — `ImageSignature`

```python
def generate_signature(
    self,
    path_or_image: str | np.ndarray,
    bytestream: bool = False
) -> np.ndarray: ...

def normalized_distance(
    self,
    target_img: np.ndarray,
    img: np.ndarray
) -> float: ...

def preprocess_image(
    self,
    path_or_image: str | np.ndarray,
    bytestream: bool = False
) -> np.ndarray: ...
```

### `signature_database_base.py` — `SignatureDatabaseBase`

```python
def add_image(
    self,
    path: str,
    img: np.ndarray | None = None,
    bytestream: bool = False,
    metadata: dict | None = None,
    refresh_after: bool = False
) -> None: ...

def search_image(
    self,
    path: str,
    all_orientations: bool = False,
    bytestream: bool = False,
    pre_filter: dict | None = None
) -> list[dict]: ...
```

### `elasticsearch_driver_es7.py` / `elasticsearch_driver_es8.py`

```python
def __init__(
    self,
    es: Elasticsearch,
    index: str = 'images',
    doc_type: str = 'image',
    timeout: str = '10s',
    size: int = 100,
    **kwargs
) -> None: ...

def delete_duplicates(self, path: str) -> None: ...
```

---

## Phase 5: CI — GitHub Actions

Replace `.travis.yml` with `.github/workflows/ci.yml`.

### Workflow Structure

- Triggers: `push` and `pull_request` to `master`
- Two jobs: `test-es7` and `test-es8`

### `test-es7` job

- Python 3.12
- Elasticsearch service: `docker.elastic.co/elasticsearch/elasticsearch:7.17.0`
  - Env: `discovery.type=single-node`, `xpack.security.enabled=false`
  - Health check on port 9200
- Install: `pip install -e .[es7,test]`
- Steps: `ruff check .`, `pytest --cov=image_match`

### `test-es8` job

- Python 3.12
- Elasticsearch service: `docker.elastic.co/elasticsearch/elasticsearch:8.13.0`
  - Env: `discovery.type=single-node`, `xpack.security.enabled=false`
  - Health check on port 9200
- Install: `pip install -e .[es8,test]`
- Steps: `ruff check .` (only in es7 job to avoid duplication), `pytest --cov=image_match`

---

## Phase 6: Tests

### Removals

- All MongoDB-related test files
- Python 2 compat code in `test_goldberg.py` (`try/except` urlretrieve, `u''` string test)

### Updates

- `test_goldberg.py`: use `from urllib.request import urlretrieve` directly
- `test_elasticsearch_driver.py`: update to import `SignatureES7` and assert deprecation warning when using `SignatureES`
- `test_elasticsearch_driver_metadata_as_nested.py`: update to use `SignatureES7` (existing test coverage for nested metadata, keep as-is otherwise)

### Additions

- `tests/test_elasticsearch_driver_es7.py`: mirrors existing ES test coverage, imports `SignatureES7`
- `tests/test_elasticsearch_driver_es8.py`: mirrors same coverage, imports `SignatureES8`

### Test Configuration

`pytest.ini` settings moved to `pyproject.toml` under `[tool.pytest.ini_options]`.

---

## File Inventory

### Added
- `pyproject.toml`
- `image_match/_es_base.py`
- `image_match/elasticsearch_driver_es7.py`
- `image_match/elasticsearch_driver_es8.py`
- `tests/test_elasticsearch_driver_es7.py`
- `tests/test_elasticsearch_driver_es8.py`
- `.github/workflows/ci.yml`

### Modified
- `image_match/goldberg.py` — remove `six`, add type hints, Python 3.12 cleanup
- `image_match/signature_database_base.py` — add type hints, Python 3.12 cleanup
- `image_match/elasticsearch_driver.py` — backward-compat re-export only
- `image_match/__init__.py` — update exports
- `tests/test_goldberg.py` — remove Python 2 compat
- `tests/test_elasticsearch_driver.py` — update imports, add deprecation warning test

### Deleted
- `setup.py`
- `pytest.ini`
- `.travis.yml`
- `image_match/mongodb_driver.py`
- `Dockerfile` (optional — depends on whether user wants to keep it)
- `docker-compose.yml` (optional — superseded by GitHub Actions services)

---

## Success Criteria

1. `pip install -e .[es7,test]` and `pip install -e .[es8,test]` both install cleanly on Python 3.12
2. All tests pass against ES 7.17 and ES 8.13 respectively
3. `ruff check .` reports no errors
4. Existing code using `from image_match.elasticsearch_driver import SignatureES` still works (with deprecation warning)
5. `from image_match.elasticsearch_driver_es7 import SignatureES7` and `from image_match.elasticsearch_driver_es8 import SignatureES8` work correctly
