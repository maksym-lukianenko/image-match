# image-match Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize the image-match library to Python 3.12, replace `setup.py` with `pyproject.toml`, remove `six`, retire the MongoDB driver, and split the Elasticsearch driver into explicit `SignatureES7` and `SignatureES8` classes.

**Architecture:** A private `_SignatureESBase` class (in `_es_base.py`) holds all shared Elasticsearch logic and inherits from `SignatureDatabaseBase`. `SignatureES7` and `SignatureES8` subclass it and each implement the version-specific API calls. The existing `elasticsearch_driver.py` becomes a thin backward-compat re-export.

**Tech Stack:** Python 3.12, setuptools (pyproject.toml), scikit-image, numpy, Pillow, elasticsearch-py 7.x or 8.x (optional extras), pytest, ruff.

**Spec:** `docs/superpowers/specs/2026-04-07-modernization-design.md`

---

### Task 1: Create pyproject.toml and delete setup.py / pytest.ini

**Files:**
- Create: `pyproject.toml`
- Delete: `setup.py`, `pytest.ini`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "image_match"
version = "2.0.0"
description = "image_match is a simple package for finding approximate image matches from a corpus."
requires-python = ">=3.12"
license = {text = "Apache License 2.0"}
authors = [
    {name = "Ryan Henderson", email = "ryan@bigchaindb.com"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Topic :: Database",
    "Topic :: Multimedia :: Graphics",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: POSIX :: Linux",
]
dependencies = [
    "scikit-image>=0.19",
    "numpy>=1.24",
    "Pillow>=9.0",
]

[project.optional-dependencies]
es7 = ["elasticsearch>=7.0.0,<8.0.0"]
es8 = ["elasticsearch>=8.0.0,<9.0.0"]
test = ["pytest", "pytest-cov", "ruff"]
dev = ["pytest", "pytest-cov", "ruff", "ipython"]
extra = ["cairosvg>=2.0"]

[tool.setuptools.packages.find]
exclude = ["tests*", "docs*", "venv*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
norecursedirs = [".*", "*.egg", "*.egg-info", "env*", "devenv*", "docs", "venv"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E501"]
```

- [ ] **Step 2: Delete setup.py and pytest.ini**

```bash
rm setup.py pytest.ini
```

- [ ] **Step 3: Verify install works**

```bash
pip install -e .[es7,test]
```

Expected: installs cleanly with no errors. `elasticsearch` 7.x and `pytest` are available.

- [ ] **Step 4: Verify pytest discovers tests**

```bash
pytest tests/test_goldberg.py --collect-only
```

Expected: lists test functions without errors.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git rm setup.py pytest.ini
git commit -m "build: replace setup.py with pyproject.toml, require Python 3.12"
```

---

### Task 2: Remove six from goldberg.py and apply Python 3.12 idioms

**Files:**
- Modify: `image_match/goldberg.py`

- [ ] **Step 1: Run existing goldberg tests to establish a baseline**

```bash
pytest tests/test_goldberg.py -v
```

Expected: all tests pass (or skip — some download images from the internet).

- [ ] **Step 2: Replace six imports and usages in goldberg.py**

Remove the import at the top of `image_match/goldberg.py`:
```python
# DELETE this line:
from six import string_types, text_type
```

Replace the string-type check in `preprocess_image` (around line 238):
```python
# OLD:
elif type(image_or_path) in string_types or \
     type(image_or_path) is text_type:
    return imread(image_or_path, as_gray=True)
elif type(image_or_path) is bytes:

# NEW:
elif isinstance(image_or_path, str):
    return imread(image_or_path, as_gray=True)
elif isinstance(image_or_path, bytes):
```

Also replace the `np.ndarray` check immediately after:
```python
# OLD:
elif type(image_or_path) is np.ndarray:

# NEW:
elif isinstance(image_or_path, np.ndarray):
```

- [ ] **Step 3: Remove explicit (object) base class**

```python
# OLD:
class ImageSignature(object):

# NEW:
class ImageSignature:
```

- [ ] **Step 4: Run tests to verify nothing broke**

```bash
pytest tests/test_goldberg.py -v
```

Expected: same results as Step 1.

- [ ] **Step 5: Commit**

```bash
git add image_match/goldberg.py
git commit -m "refactor: remove six dependency, use Python 3.12 str/bytes idioms in goldberg"
```

---

### Task 3: Apply Python 3.12 idioms to signature_database_base.py

**Files:**
- Modify: `image_match/signature_database_base.py`

- [ ] **Step 1: Replace type() checks with isinstance() in signature_database_base.py**

In `__init__`, replace all three type checks (around lines 167-180):
```python
# OLD:
if type(k) is not int:
    raise TypeError('k should be an integer')
if type(N) is not int:
    raise TypeError('N should be an integer')
if type(n_grid) is not int:
    raise TypeError('n_grid should be an integer')
# ...
if type(distance_cutoff) is not float:
    raise TypeError('distance_cutoff should be a float')

# NEW:
if not isinstance(k, int):
    raise TypeError('k should be an integer')
if not isinstance(N, int):
    raise TypeError('N should be an integer')
if not isinstance(n_grid, int):
    raise TypeError('n_grid should be an integer')
# ...
if not isinstance(distance_cutoff, float):
    raise TypeError('distance_cutoff should be a float')
```

Remove explicit `(object)` base class from `SignatureDatabaseBase`:
```python
# OLD:
class SignatureDatabaseBase(object):

# NEW:
class SignatureDatabaseBase:
```

- [ ] **Step 2: Run goldberg tests to verify**

```bash
pytest tests/test_goldberg.py -v
```

Expected: all tests still pass.

- [ ] **Step 3: Commit**

```bash
git add image_match/signature_database_base.py
git commit -m "refactor: use isinstance() and implicit object base in signature_database_base"
```

---

### Task 4: Delete MongoDB driver

**Files:**
- Delete: `image_match/mongodb_driver.py`

- [ ] **Step 1: Delete the MongoDB driver**

```bash
git rm image_match/mongodb_driver.py
```

- [ ] **Step 2: Verify no remaining imports of mongodb_driver**

```bash
grep -r "mongodb_driver" image_match/ tests/
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: retire MongoDB driver"
```

---

### Task 5: Create image_match/_es_base.py

**Files:**
- Create: `image_match/_es_base.py`

- [ ] **Step 1: Create image_match/_es_base.py with full content**

```python
from abc import abstractmethod
from datetime import datetime

import numpy as np

from image_match.signature_database_base import SignatureDatabaseBase, normalized_distance


class _SignatureESBase(SignatureDatabaseBase):
    """Private base class for Elasticsearch drivers.

    Subclasses must implement:
        - search_single_record
        - insert_single_record
        - _get_doc_source(hit) -> dict
        - _search_by_path(path) -> list[dict]
    """

    def __init__(self, es, index='images', doc_type='image', timeout='10s', size=100,
                 *args, **kwargs):
        self.es = es
        self.index = index
        self.doc_type = doc_type
        self.timeout = timeout
        self.size = size
        super().__init__(*args, **kwargs)

    @abstractmethod
    def _get_doc_source(self, hit: dict) -> dict:
        """Extract the document fields from a raw ES hit.

        ES7 stores data nested under doc_type; ES8 stores at root.
        """
        raise NotImplementedError

    @abstractmethod
    def _search_by_path(self, path: str) -> list:
        """Return raw ES hits whose path field matches the given path."""
        raise NotImplementedError

    def _format_results(self, res: list, signature: list) -> list[dict]:
        """Compute distances and format ES hits into result dicts."""
        sigs = np.array([self._get_doc_source(x)['signature'] for x in res])

        if sigs.size == 0:
            return []

        dists = normalized_distance(sigs, np.array(signature))

        formatted_res = []
        for x in res:
            source = self._get_doc_source(x)
            formatted_res.append({
                'id': x['_id'],
                'score': x['_score'],
                'metadata': source.get('metadata'),
                'path': source.get('url', source.get('path')),
            })

        for i, row in enumerate(formatted_res):
            row['dist'] = dists[i]

        return list(filter(lambda y: y['dist'] < self.distance_cutoff, formatted_res))

    def delete_duplicates(self, path: str) -> None:
        """Delete all but one entry whose path matches the given path."""
        hits = self._search_by_path(path)
        matching_ids = [
            hit['_id'] for hit in hits
            if self._get_doc_source(hit).get('path') == path
        ]
        for id_tag in matching_ids[1:]:
            self.es.delete(index=self.index, id=id_tag)
```

- [ ] **Step 2: Verify the module imports cleanly**

```bash
python -c "from image_match._es_base import _SignatureESBase; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add image_match/_es_base.py
git commit -m "feat: add _SignatureESBase shared ES driver base class"
```

---

### Task 6: Create image_match/elasticsearch_driver_es7.py

**Files:**
- Create: `image_match/elasticsearch_driver_es7.py`

- [ ] **Step 1: Write the failing import test**

```bash
python -c "from image_match.elasticsearch_driver_es7 import SignatureES7"
```

Expected: `ModuleNotFoundError`

- [ ] **Step 2: Create image_match/elasticsearch_driver_es7.py**

```python
from datetime import datetime

import numpy as np

from image_match._es_base import _SignatureESBase


class SignatureES7(_SignatureESBase):
    """Elasticsearch 7.x driver for image-match.

    Install the client with: pip install image-match[es7]

    Example::

        from elasticsearch import Elasticsearch
        from image_match.elasticsearch_driver_es7 import SignatureES7

        es = Elasticsearch()
        ses = SignatureES7(es)
        ses.add_image('path/to/image.jpg')
        results = ses.search_image('path/to/query.jpg')
    """

    def _get_doc_source(self, hit: dict) -> dict:
        return hit['_source'][self.doc_type]

    def _search_by_path(self, path: str) -> list:
        return self.es.search(
            body={'query': {'match': {f'{self.doc_type}.path': path}}},
            index=self.index,
        )['hits']['hits']

    def search_single_record(self, rec, pre_filter=None):
        path = rec.pop('path')
        signature = rec.pop('signature')
        rec.pop('metadata', None)

        should = [
            {'term': {f'{self.doc_type}.{word}': rec[word]}}
            for word in rec
        ]
        body = {
            'query': {'bool': {'should': should}},
            '_source': {'excludes': [f'{self.doc_type}.simple_word_*']},
        }
        if pre_filter is not None:
            body['query']['bool']['filter'] = pre_filter

        res = self.es.search(
            index=self.index,
            body=body,
            size=self.size,
            timeout=self.timeout,
        )['hits']['hits']

        return self._format_results(res, signature)

    def insert_single_record(self, rec, refresh_after=False):
        rec['timestamp'] = datetime.now()
        self.es.index(
            index=self.index,
            body={self.doc_type: rec},
            refresh=refresh_after,
        )
```

- [ ] **Step 3: Verify the module imports cleanly**

```bash
python -c "from image_match.elasticsearch_driver_es7 import SignatureES7; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add image_match/elasticsearch_driver_es7.py
git commit -m "feat: add SignatureES7 for Elasticsearch 7.x"
```

---

### Task 7: Create image_match/elasticsearch_driver_es8.py

**Files:**
- Create: `image_match/elasticsearch_driver_es8.py`

- [ ] **Step 1: Write the failing import test**

```bash
python -c "from image_match.elasticsearch_driver_es8 import SignatureES8"
```

Expected: `ModuleNotFoundError`

- [ ] **Step 2: Create image_match/elasticsearch_driver_es8.py**

```python
from datetime import datetime

import numpy as np

from image_match._es_base import _SignatureESBase


class SignatureES8(_SignatureESBase):
    """Elasticsearch 8.x driver for image-match.

    Install the client with: pip install image-match[es8]

    Note: Documents are stored without doc_type nesting — the signature
    and all fields are at the root of the document. This is incompatible
    with data stored by SignatureES7.

    Example::

        from elasticsearch import Elasticsearch
        from image_match.elasticsearch_driver_es8 import SignatureES8

        es = Elasticsearch()
        ses = SignatureES8(es)
        ses.add_image('path/to/image.jpg')
        results = ses.search_image('path/to/query.jpg')
    """

    def _get_doc_source(self, hit: dict) -> dict:
        return hit['_source']

    def _search_by_path(self, path: str) -> list:
        return self.es.search(
            query={'match': {'path': path}},
            index=self.index,
        )['hits']['hits']

    def search_single_record(self, rec, pre_filter=None):
        path = rec.pop('path')
        signature = rec.pop('signature')
        rec.pop('metadata', None)

        should = [{'term': {word: rec[word]}} for word in rec]
        query = {'bool': {'should': should}}
        if pre_filter is not None:
            query['bool']['filter'] = pre_filter

        res = self.es.search(
            index=self.index,
            query=query,
            source_excludes=['simple_word_*'],
            size=self.size,
            timeout=self.timeout,
        )['hits']['hits']

        return self._format_results(res, signature)

    def insert_single_record(self, rec, refresh_after=False):
        rec['timestamp'] = datetime.now()
        self.es.index(
            index=self.index,
            document=rec,
            refresh=refresh_after,
        )
```

- [ ] **Step 3: Verify the module imports cleanly**

```bash
python -c "from image_match.elasticsearch_driver_es8 import SignatureES8; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add image_match/elasticsearch_driver_es8.py
git commit -m "feat: add SignatureES8 for Elasticsearch 8.x"
```

---

### Task 8: Update elasticsearch_driver.py for backward compatibility

**Files:**
- Modify: `image_match/elasticsearch_driver.py`

- [ ] **Step 1: Replace the full content of elasticsearch_driver.py**

```python
"""Backward-compatibility shim for image_match.elasticsearch_driver.

Use SignatureES7 or SignatureES8 directly instead:

    from image_match.elasticsearch_driver_es7 import SignatureES7
    from image_match.elasticsearch_driver_es8 import SignatureES8
"""
import warnings

from image_match.elasticsearch_driver_es7 import SignatureES7
from image_match.elasticsearch_driver_es8 import SignatureES8


def SignatureES(*args, **kwargs):
    """Deprecated. Use SignatureES7 or SignatureES8 explicitly."""
    warnings.warn(
        "SignatureES is deprecated. Use SignatureES7 (for ES 7.x) or "
        "SignatureES8 (for ES 8.x) from their respective modules.",
        DeprecationWarning,
        stacklevel=2,
    )
    return SignatureES7(*args, **kwargs)


__all__ = ['SignatureES', 'SignatureES7', 'SignatureES8']
```

- [ ] **Step 2: Update image_match/__init__.py to export the new driver classes**

```python
__author__ = 'ryan'
__version__ = '2.0.0'

from image_match.elasticsearch_driver_es7 import SignatureES7
from image_match.elasticsearch_driver_es8 import SignatureES8

__all__ = ['SignatureES7', 'SignatureES8']
```

- [ ] **Step 4: Verify backward-compat import still works**

```bash
python -c "
import warnings
warnings.filterwarnings('error')
from image_match.elasticsearch_driver import SignatureES7, SignatureES8
print('Direct imports OK')
"
```

Expected: `Direct imports OK`

- [ ] **Step 5: Verify deprecation warning fires for SignatureES on call**

```bash
python -c "
import warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter('always')
    from image_match.elasticsearch_driver import SignatureES
    print('Import OK, warning fires on call (not import)')
"
```

Expected: `Import OK, warning fires on call (not import)`

- [ ] **Step 6: Commit**

```bash
git add image_match/elasticsearch_driver.py image_match/__init__.py
git commit -m "feat: convert elasticsearch_driver.py to backward-compat re-export, update __init__ exports"
```

---

### Task 9: Update tests/test_elasticsearch_driver.py to use SignatureES7

**Files:**
- Modify: `tests/test_elasticsearch_driver.py`

- [ ] **Step 1: Replace the full content of tests/test_elasticsearch_driver.py**

```python
import hashlib
import os
import warnings
from time import sleep

import pytest
from elasticsearch import Elasticsearch, ConnectionError, NotFoundError, RequestError
from PIL import Image
from urllib.request import urlretrieve

from image_match.elasticsearch_driver import SignatureES
from image_match.elasticsearch_driver_es7 import SignatureES7

test_img_url1 = 'https://camo.githubusercontent.com/810bdde0a88bc3f8ce70c5d85d8537c37f707abe/68747470733a2f2f75706c6f61642e77696b696d656469612e6f72672f77696b6970656469612f636f6d6d6f6e732f7468756d622f652f65632f4d6f6e615f4c6973612c5f62795f4c656f6e6172646f5f64615f56696e63692c5f66726f6d5f4332524d465f7265746f75636865642e6a70672f36383770782d4d6f6e615f4c6973612c5f62795f4c656f6e6172646f5f64615f56696e63692c5f66726f6d5f4332524d465f7265746f75636865642e6a7067'
test_img_url2 = 'https://camo.githubusercontent.com/826e23bc3eca041110a5af467671b012606aa406/68747470733a2f2f63322e737461746963666c69636b722e636f6d2f382f373135382f363831343434343939315f303864383264653537655f7a2e6a7067'
urlretrieve(test_img_url1, 'test1.jpg')
urlretrieve(test_img_url2, 'test2.jpg')

INDEX_NAME = 'test_environment_{}'.format(hashlib.md5(os.urandom(128)).hexdigest()[:12])
DOC_TYPE = 'image'
MAPPINGS = {
    "mappings": {
        "properties": {
            DOC_TYPE: {
                "properties": {
                    "path": {"type": "keyword"},
                    "metadata": {
                        "properties": {
                            "tenant_id": {"type": "keyword"}
                        }
                    }
                }
            }
        }
    }
}


@pytest.fixture(scope='module', autouse=True)
def index_name():
    return INDEX_NAME


@pytest.fixture(scope='function', autouse=True)
def setup_index(request, index_name):
    es = Elasticsearch()
    try:
        es.indices.create(index=index_name, body=MAPPINGS)
    except RequestError as e:
        if e.error == 'resource_already_exists_exception':
            es.indices.delete(index_name)
        else:
            raise

    def fin():
        try:
            es.indices.delete(index_name)
        except NotFoundError:
            pass

    request.addfinalizer(fin)


@pytest.fixture(scope='function', autouse=True)
def cleanup_index(request, es, index_name):
    def fin():
        try:
            es.indices.delete(index_name)
        except NotFoundError:
            pass

    request.addfinalizer(fin)


@pytest.fixture
def es():
    return Elasticsearch()


@pytest.fixture
def ses(es, index_name):
    return SignatureES7(es=es, index=index_name, doc_type=DOC_TYPE)


def test_elasticsearch_running(es):
    for i in range(5):
        try:
            es.ping()
            return
        except ConnectionError:
            sleep(2)
    pytest.fail('Elasticsearch not running (failed to connect after 5 tries)')


def test_signaturees_emits_deprecation_warning(es, index_name):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        SignatureES(es=es, index=index_name, doc_type=DOC_TYPE)
    assert len(w) == 1
    assert issubclass(w[0].category, DeprecationWarning)
    assert 'SignatureES7' in str(w[0].message)


def test_add_image_by_url(ses):
    ses.add_image(test_img_url1)
    ses.add_image(test_img_url2)
    assert True


def test_add_image_by_path(ses):
    ses.add_image('test1.jpg')
    assert True


def test_index_refresh(ses):
    ses.add_image('test1.jpg', refresh_after=True)
    r = ses.search_image('test1.jpg')
    assert len(r) == 1


def test_add_image_as_bytestream(ses):
    with open('test1.jpg', 'rb') as f:
        ses.add_image('bytestream_test', img=f.read(), bytestream=True)
    assert True


def test_add_image_with_different_name(ses):
    ses.add_image('custom_name_test', img='test1.jpg', bytestream=False)
    assert True


def test_lookup_from_url(ses):
    ses.add_image('test1.jpg', refresh_after=True)
    r = ses.search_image(test_img_url1)
    assert len(r) == 1
    assert r[0]['path'] == 'test1.jpg'
    assert 'score' in r[0]
    assert 'dist' in r[0]
    assert 'id' in r[0]


def test_lookup_from_file(ses):
    ses.add_image('test1.jpg', refresh_after=True)
    r = ses.search_image('test1.jpg')
    assert len(r) == 1
    assert r[0]['path'] == 'test1.jpg'
    assert 'score' in r[0]
    assert 'dist' in r[0]
    assert 'id' in r[0]


def test_lookup_from_bytestream(ses):
    ses.add_image('test1.jpg', refresh_after=True)
    with open('test1.jpg', 'rb') as f:
        r = ses.search_image(f.read(), bytestream=True)
    assert len(r) == 1
    assert r[0]['path'] == 'test1.jpg'
    assert 'score' in r[0]
    assert 'dist' in r[0]
    assert 'id' in r[0]


def test_lookup_with_cutoff(ses):
    ses.add_image('test2.jpg', refresh_after=True)
    ses.distance_cutoff = 0.01
    r = ses.search_image('test1.jpg')
    assert len(r) == 0


def test_add_image_with_metadata(ses):
    metadata = {'some_info': {'test': 'ok!'}}
    ses.add_image('test1.jpg', metadata=metadata, refresh_after=True)
    r = ses.search_image('test1.jpg')
    assert r[0]['metadata'] == metadata
    assert 'path' in r[0]
    assert 'score' in r[0]
    assert 'dist' in r[0]
    assert 'id' in r[0]


def test_lookup_with_filter_by_metadata(ses):
    metadata = {'tenant_id': 'foo'}
    ses.add_image('test1.jpg', metadata=metadata, refresh_after=True)
    metadata2 = {'tenant_id': 'bar-2'}
    ses.add_image('test2.jpg', metadata=metadata2, refresh_after=True)

    r = ses.search_image('test1.jpg', pre_filter={"term": {f'{DOC_TYPE}.metadata.tenant_id': "foo"}})
    assert len(r) == 1
    assert r[0]['metadata'] == metadata

    r = ses.search_image('test1.jpg', pre_filter={"term": {f'{DOC_TYPE}.metadata.tenant_id': "bar-2"}})
    assert len(r) == 1
    assert r[0]['metadata'] == metadata2

    r = ses.search_image('test1.jpg', pre_filter={"term": {f'{DOC_TYPE}.metadata.tenant_id': "bar-3"}})
    assert len(r) == 0


def test_all_orientations(ses):
    im = Image.open('test1.jpg')
    im.rotate(90, expand=True).save('rotated_test1.jpg')

    ses.add_image('test1.jpg', refresh_after=True)
    r = ses.search_image('rotated_test1.jpg', all_orientations=True)
    assert len(r) == 1
    assert r[0]['path'] == 'test1.jpg'
    assert r[0]['dist'] < 0.05

    with open('rotated_test1.jpg', 'rb') as f:
        r = ses.search_image(f.read(), bytestream=True, all_orientations=True)
        assert len(r) == 1
        assert r[0]['dist'] < 0.05


def test_duplicate(ses):
    ses.add_image('test1.jpg', refresh_after=True)
    ses.add_image('test1.jpg', refresh_after=True)
    r = ses.search_image('test1.jpg')
    assert len(r) == 2
    assert r[0]['path'] == 'test1.jpg'
    assert 'score' in r[0]
    assert 'dist' in r[0]
    assert 'id' in r[0]


def test_duplicate_removal(ses):
    for i in range(10):
        ses.add_image('test1.jpg')
    sleep(1)
    r = ses.search_image('test1.jpg')
    assert len(r) == 10
    ses.delete_duplicates('test1.jpg')
    sleep(1)
    r = ses.search_image('test1.jpg')
    assert len(r) == 1
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_elasticsearch_driver.py
git commit -m "test: update ES driver test to use SignatureES7, add deprecation warning test"
```

---

### Task 10: Update tests/test_elasticsearch_driver_metadata_as_nested.py

**Files:**
- Modify: `tests/test_elasticsearch_driver_metadata_as_nested.py`

- [ ] **Step 1: Replace the full content**

```python
import hashlib
import os
from time import sleep

import pytest
from elasticsearch import Elasticsearch, ConnectionError, NotFoundError, RequestError
from urllib.request import urlretrieve

from image_match.elasticsearch_driver_es7 import SignatureES7

test_img_url1 = 'https://camo.githubusercontent.com/810bdde0a88bc3f8ce70c5d85d8537c37f707abe/68747470733a2f2f75706c6f61642e77696b696d656469612e6f72672f77696b6970656469612f636f6d6d6f6e732f7468756d622f652f65632f4d6f6e615f4c6973612c5f62795f4c656f6e6172646f5f64615f56696e63692c5f66726f6d5f4332524d465f7265746f75636865642e6a70672f36383770782d4d6f6e615f4c6973612c5f62795f4c656f6e6172646f5f64615f56696e63692c5f66726f6d5f4332524d465f7265746f75636865642e6a7067'
test_img_url2 = 'https://camo.githubusercontent.com/826e23bc3eca041110a5af467671b012606aa406/68747470733a2f2f63322e737461746963666c69636b722e636f6d2f382f373135382f363831343434343939315f303864383264653537655f7a2e6a7067'
urlretrieve(test_img_url1, 'test1.jpg')
urlretrieve(test_img_url2, 'test2.jpg')

INDEX_NAME = 'test_environment_{}'.format(hashlib.md5(os.urandom(128)).hexdigest()[:12])
DOC_TYPE = 'image'
MAPPINGS = {
    "mappings": {
        "properties": {
            DOC_TYPE: {
                "properties": {
                    "path": {"type": "keyword"},
                    "metadata": {
                        "properties": {
                            "tenant_id": {"type": "keyword"},
                            "project_id": {"type": "keyword"},
                        }
                    }
                }
            }
        }
    }
}


@pytest.fixture(scope='module', autouse=True)
def index_name():
    return INDEX_NAME


@pytest.fixture(scope='function', autouse=True)
def setup_index(request, index_name):
    es = Elasticsearch()
    try:
        es.indices.create(index=index_name, body=MAPPINGS)
    except RequestError as e:
        if e.error == 'index_already_exists_exception':
            es.indices.delete(index_name)
        else:
            raise

    def fin():
        try:
            es.indices.delete(index_name)
        except NotFoundError:
            pass

    request.addfinalizer(fin)


@pytest.fixture(scope='function', autouse=True)
def cleanup_index(request, es, index_name):
    def fin():
        try:
            es.indices.delete(index_name)
        except NotFoundError:
            pass

    request.addfinalizer(fin)


@pytest.fixture
def es():
    return Elasticsearch()


@pytest.fixture
def ses(es, index_name):
    return SignatureES7(es=es, index=index_name, doc_type=DOC_TYPE)


def test_elasticsearch_running(es):
    for i in range(5):
        try:
            es.ping()
            return
        except ConnectionError:
            sleep(2)
    pytest.fail('Elasticsearch not running (failed to connect after 5 tries)')


def test_lookup_with_filter_by_metadata(ses):
    ses.add_image('test1.jpg', metadata=_metadata('foo', 'project-x'), refresh_after=True)
    ses.add_image('test2.jpg', metadata=_metadata('foo', 'project-x'), refresh_after=True)
    ses.add_image('test3.jpg', img='test1.jpg', metadata=_metadata('foo', 'project-y'), refresh_after=True)
    ses.add_image('test2.jpg', metadata=_metadata('bar', 'project-x'), refresh_after=True)

    r = ses.search_image('test1.jpg', pre_filter=_nested_filter('foo', 'project-x'))
    assert len(r) == 2

    r = ses.search_image('test1.jpg', pre_filter=_nested_filter('foo', 'project-z'))
    assert len(r) == 0

    r = ses.search_image('test1.jpg', pre_filter=_nested_filter('bar', 'project-x'))
    assert len(r) == 1

    r = ses.search_image('test1.jpg', pre_filter=_nested_filter('bar-2', 'project-x'))
    assert len(r) == 0

    r = ses.search_image('test1.jpg', pre_filter=_nested_filter('bar', 'project-z'))
    assert len(r) == 0


def _metadata(tenant_id, project_id):
    return {'tenant_id': tenant_id, 'project_id': project_id}


def _nested_filter(tenant_id, project_id):
    return [
        {"term": {"image.metadata.tenant_id": tenant_id}},
        {"term": {"image.metadata.project_id": project_id}},
    ]
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_elasticsearch_driver_metadata_as_nested.py
git commit -m "test: update nested metadata test to use SignatureES7 directly"
```

---

### Task 11: Create tests/test_elasticsearch_driver_es8.py

**Files:**
- Create: `tests/test_elasticsearch_driver_es8.py`

- [ ] **Step 1: Create tests/test_elasticsearch_driver_es8.py**

```python
import hashlib
import os
from time import sleep

import pytest
from elasticsearch import Elasticsearch, ConnectionError, NotFoundError
from PIL import Image
from urllib.request import urlretrieve

from image_match.elasticsearch_driver_es8 import SignatureES8

test_img_url1 = 'https://camo.githubusercontent.com/810bdde0a88bc3f8ce70c5d85d8537c37f707abe/68747470733a2f2f75706c6f61642e77696b696d656469612e6f72672f77696b6970656469612f636f6d6d6f6e732f7468756d622f652f65632f4d6f6e615f4c6973612c5f62795f4c656f6e6172646f5f64615f56696e63692c5f66726f6d5f4332524d465f7265746f75636865642e6a70672f36383770782d4d6f6e615f4c6973612c5f62795f4c656f6e6172646f5f64615f56696e63692c5f66726f6d5f4332524d465f7265746f75636865642e6a7067'
test_img_url2 = 'https://camo.githubusercontent.com/826e23bc3eca041110a5af467671b012606aa406/68747470733a2f2f63322e737461746963666c69636b722e636f6d2f382f373135382f363831343434343939315f303864383264653537655f7a2e6a7067'
urlretrieve(test_img_url1, 'test1.jpg')
urlretrieve(test_img_url2, 'test2.jpg')

INDEX_NAME = 'test_environment_{}'.format(hashlib.md5(os.urandom(128)).hexdigest()[:12])
# ES8 mappings: no doc_type nesting, fields at root level
MAPPINGS = {
    "properties": {
        "path": {"type": "keyword"},
        "metadata": {
            "properties": {
                "tenant_id": {"type": "keyword"},
            }
        }
    }
}


@pytest.fixture(scope='module', autouse=True)
def index_name():
    return INDEX_NAME


@pytest.fixture(scope='function', autouse=True)
def setup_index(request, index_name):
    es = Elasticsearch()
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)
    es.indices.create(index=index_name, mappings=MAPPINGS)

    def fin():
        if es.indices.exists(index=index_name):
            es.indices.delete(index=index_name)

    request.addfinalizer(fin)


@pytest.fixture(scope='function', autouse=True)
def cleanup_index(request, es, index_name):
    def fin():
        if es.indices.exists(index=index_name):
            es.indices.delete(index=index_name)

    request.addfinalizer(fin)


@pytest.fixture
def es():
    return Elasticsearch()


@pytest.fixture
def ses(es, index_name):
    return SignatureES8(es=es, index=index_name)


def test_elasticsearch_running(es):
    for i in range(5):
        try:
            es.ping()
            return
        except ConnectionError:
            sleep(2)
    pytest.fail('Elasticsearch not running (failed to connect after 5 tries)')


def test_add_image_by_url(ses):
    ses.add_image(test_img_url1)
    ses.add_image(test_img_url2)
    assert True


def test_add_image_by_path(ses):
    ses.add_image('test1.jpg')
    assert True


def test_index_refresh(ses):
    ses.add_image('test1.jpg', refresh_after=True)
    r = ses.search_image('test1.jpg')
    assert len(r) == 1


def test_add_image_as_bytestream(ses):
    with open('test1.jpg', 'rb') as f:
        ses.add_image('bytestream_test', img=f.read(), bytestream=True)
    assert True


def test_add_image_with_different_name(ses):
    ses.add_image('custom_name_test', img='test1.jpg', bytestream=False)
    assert True


def test_lookup_from_url(ses):
    ses.add_image('test1.jpg', refresh_after=True)
    r = ses.search_image(test_img_url1)
    assert len(r) == 1
    assert r[0]['path'] == 'test1.jpg'
    assert 'score' in r[0]
    assert 'dist' in r[0]
    assert 'id' in r[0]


def test_lookup_from_file(ses):
    ses.add_image('test1.jpg', refresh_after=True)
    r = ses.search_image('test1.jpg')
    assert len(r) == 1
    assert r[0]['path'] == 'test1.jpg'
    assert 'score' in r[0]
    assert 'dist' in r[0]
    assert 'id' in r[0]


def test_lookup_from_bytestream(ses):
    ses.add_image('test1.jpg', refresh_after=True)
    with open('test1.jpg', 'rb') as f:
        r = ses.search_image(f.read(), bytestream=True)
    assert len(r) == 1
    assert r[0]['path'] == 'test1.jpg'
    assert 'score' in r[0]
    assert 'dist' in r[0]
    assert 'id' in r[0]


def test_lookup_with_cutoff(ses):
    ses.add_image('test2.jpg', refresh_after=True)
    ses.distance_cutoff = 0.01
    r = ses.search_image('test1.jpg')
    assert len(r) == 0


def test_add_image_with_metadata(ses):
    metadata = {'some_info': {'test': 'ok!'}}
    ses.add_image('test1.jpg', metadata=metadata, refresh_after=True)
    r = ses.search_image('test1.jpg')
    assert r[0]['metadata'] == metadata
    assert 'path' in r[0]
    assert 'score' in r[0]
    assert 'dist' in r[0]
    assert 'id' in r[0]


def test_lookup_with_filter_by_metadata(ses):
    # ES8: filter fields have no doc_type prefix
    metadata = {'tenant_id': 'foo'}
    ses.add_image('test1.jpg', metadata=metadata, refresh_after=True)
    metadata2 = {'tenant_id': 'bar-2'}
    ses.add_image('test2.jpg', metadata=metadata2, refresh_after=True)

    r = ses.search_image('test1.jpg', pre_filter={"term": {"metadata.tenant_id": "foo"}})
    assert len(r) == 1
    assert r[0]['metadata'] == metadata

    r = ses.search_image('test1.jpg', pre_filter={"term": {"metadata.tenant_id": "bar-2"}})
    assert len(r) == 1
    assert r[0]['metadata'] == metadata2

    r = ses.search_image('test1.jpg', pre_filter={"term": {"metadata.tenant_id": "bar-3"}})
    assert len(r) == 0


def test_all_orientations(ses):
    im = Image.open('test1.jpg')
    im.rotate(90, expand=True).save('rotated_test1.jpg')

    ses.add_image('test1.jpg', refresh_after=True)
    r = ses.search_image('rotated_test1.jpg', all_orientations=True)
    assert len(r) == 1
    assert r[0]['path'] == 'test1.jpg'
    assert r[0]['dist'] < 0.05

    with open('rotated_test1.jpg', 'rb') as f:
        r = ses.search_image(f.read(), bytestream=True, all_orientations=True)
        assert len(r) == 1
        assert r[0]['dist'] < 0.05


def test_duplicate(ses):
    ses.add_image('test1.jpg', refresh_after=True)
    ses.add_image('test1.jpg', refresh_after=True)
    r = ses.search_image('test1.jpg')
    assert len(r) == 2
    assert r[0]['path'] == 'test1.jpg'


def test_duplicate_removal(ses):
    for i in range(10):
        ses.add_image('test1.jpg')
    sleep(1)
    r = ses.search_image('test1.jpg')
    assert len(r) == 10
    ses.delete_duplicates('test1.jpg')
    sleep(1)
    r = ses.search_image('test1.jpg')
    assert len(r) == 1
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_elasticsearch_driver_es8.py
git commit -m "test: add ES8 integration test suite"
```

---

### Task 12: Add type hints to goldberg.py public API

**Files:**
- Modify: `image_match/goldberg.py`

- [ ] **Step 1: Add numpy import alias (already imported, just ensure it's there) and add type hints to generate_signature**

Find the `generate_signature` method signature and update it:
```python
# OLD:
def generate_signature(self, path_or_image, bytestream=False):

# NEW:
def generate_signature(self, path_or_image: str | np.ndarray, bytestream: bool = False) -> np.ndarray:
```

- [ ] **Step 2: Add type hints to preprocess_image**

```python
# OLD:
@staticmethod
def preprocess_image(image_or_path, bytestream=False, handle_mpo=False):

# NEW:
@staticmethod
def preprocess_image(image_or_path: str | bytes | np.ndarray, bytestream: bool = False, handle_mpo: bool = False) -> np.ndarray:
```

- [ ] **Step 3: Add type hints to normalized_distance instance method**

Find the `normalized_distance` method on `ImageSignature` (not the module-level function) and update it:
```python
# OLD:
def normalized_distance(self, target_img, img):

# NEW:
def normalized_distance(self, target_img: np.ndarray, img: np.ndarray) -> float:
```

- [ ] **Step 4: Run goldberg tests**

```bash
pytest tests/test_goldberg.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add image_match/goldberg.py
git commit -m "feat: add type hints to ImageSignature public API"
```

---

### Task 13: Add type hints to signature_database_base.py public API

**Files:**
- Modify: `image_match/signature_database_base.py`

- [ ] **Step 1: Add numpy import and type hints to add_image**

```python
# OLD:
def add_image(self, path, img=None, bytestream=False, metadata=None, refresh_after=False):

# NEW:
def add_image(self, path: str, img: np.ndarray | None = None, bytestream: bool = False,
              metadata: dict | None = None, refresh_after: bool = False) -> None:
```

- [ ] **Step 2: Add type hints to search_image**

```python
# OLD:
def search_image(self, path, all_orientations=False, bytestream=False, pre_filter=None):

# NEW:
def search_image(self, path: str, all_orientations: bool = False, bytestream: bool = False,
                 pre_filter: dict | list | None = None) -> list[dict]:
```

- [ ] **Step 3: Run goldberg tests**

```bash
pytest tests/test_goldberg.py -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add image_match/signature_database_base.py
git commit -m "feat: add type hints to SignatureDatabaseBase public API"
```

---

### Task 14: Add type hints to ES driver public API

**Files:**
- Modify: `image_match/_es_base.py`
- Modify: `image_match/elasticsearch_driver_es7.py`
- Modify: `image_match/elasticsearch_driver_es8.py`

- [ ] **Step 1: Add Elasticsearch type import and __init__ type hints to _es_base.py**

At the top of `_es_base.py`, add:
```python
from elasticsearch import Elasticsearch
```

Update `__init__`:
```python
# OLD:
def __init__(self, es, index='images', doc_type='image', timeout='10s', size=100,
             *args, **kwargs):

# NEW:
def __init__(self, es: Elasticsearch, index: str = 'images', doc_type: str = 'image',
             timeout: str = '10s', size: int = 100, *args, **kwargs):
```

- [ ] **Step 2: Add type hints to SignatureES7.__init__ and delete_duplicates**

In `elasticsearch_driver_es7.py`, add the import at top:
```python
from elasticsearch import Elasticsearch
```

The `__init__` is inherited from `_SignatureESBase` and already typed — no change needed.

Add return type to `delete_duplicates` in `_es_base.py` (already done in Task 5 — verify it has `-> None`).

- [ ] **Step 3: Add Elasticsearch import to elasticsearch_driver_es8.py**

```python
from elasticsearch import Elasticsearch
```

The `__init__` is inherited — no change needed.

- [ ] **Step 4: Verify imports clean**

```bash
python -c "
from image_match.elasticsearch_driver_es7 import SignatureES7
from image_match.elasticsearch_driver_es8 import SignatureES8
print('OK')
"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add image_match/_es_base.py image_match/elasticsearch_driver_es7.py image_match/elasticsearch_driver_es8.py
git commit -m "feat: add type hints to ES driver public API"
```

---

### Task 15: Create .github/workflows/ci.yml

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the GitHub Actions workflow**

```bash
mkdir -p .github/workflows
```

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

jobs:
  test-es7:
    name: Tests (Elasticsearch 7.x)
    runs-on: ubuntu-latest

    services:
      elasticsearch:
        image: docker.elastic.co/elasticsearch/elasticsearch:7.17.0
        env:
          discovery.type: single-node
          xpack.security.enabled: "false"
          xpack.monitoring.enabled: "false"
        ports:
          - 9200:9200
        options: >-
          --health-cmd "curl -f http://localhost:9200/_cluster/health"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 10

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -e .[es7,test]

      - name: Lint
        run: ruff check .

      - name: Run tests
        run: pytest --cov=image_match --ignore=tests/test_elasticsearch_driver_es8.py

  test-es8:
    name: Tests (Elasticsearch 8.x)
    runs-on: ubuntu-latest

    services:
      elasticsearch:
        image: docker.elastic.co/elasticsearch/elasticsearch:8.13.0
        env:
          discovery.type: single-node
          xpack.security.enabled: "false"
        ports:
          - 9200:9200
        options: >-
          --health-cmd "curl -f http://localhost:9200/_cluster/health"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 10

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -e .[es8,test]

      - name: Run tests
        run: pytest tests/test_goldberg.py tests/test_elasticsearch_driver_es8.py --cov=image_match
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: replace Travis CI with GitHub Actions, add es7 and es8 jobs"
```

---

### Task 16: Delete legacy files

**Files:**
- Delete: `.travis.yml`

- [ ] **Step 1: Delete .travis.yml**

```bash
git rm .travis.yml
git commit -m "ci: delete .travis.yml (replaced by GitHub Actions)"
```

- [ ] **Step 2: Run ruff to verify no linting errors**

```bash
ruff check .
```

Expected: no output (no errors).

- [ ] **Step 3: If ruff reports errors, fix them**

Common issues ruff catches:
- Unused imports: remove them
- f-string without placeholders: convert to plain string
- `E501` (line too long): ruff's default is 88 chars — fix any violations

After fixing:
```bash
ruff check .
```

Expected: no output.

- [ ] **Step 4: Commit any ruff fixes**

```bash
git add -p
git commit -m "style: fix ruff linting issues"
```

---

### Task 17: Update spec checkboxes

**Files:**
- Modify: `docs/superpowers/specs/2026-04-07-modernization-design.md`

- [ ] **Step 1: Tick all checkboxes in the spec**

Open `docs/superpowers/specs/2026-04-07-modernization-design.md` and change every `- [ ]` to `- [x]`.

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-04-07-modernization-design.md
git commit -m "docs: mark all modernization spec items as complete"
```
