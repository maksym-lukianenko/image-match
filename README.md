# image-match

A Python library for finding approximate image matches from a corpus, backed by Elasticsearch.

This is a maintained fork of the original [image-match](https://github.com/edjo-labs/image-match) library (no longer maintained upstream).

Based on the paper [_An image signature for any kind of image_, Wong et al](http://www.cs.cmu.edu/~hcwong/Pdfs/icip02.ps).

**Note:** This algorithm finds nearly duplicate images (e.g. copyright violation detection). It is **not** intended to find conceptually similar images.

---

## Requirements

- Python 3.12+
- Elasticsearch 7.x or 8.x

---

## Installation

Choose the extra matching your Elasticsearch version:

```bash
# Elasticsearch 7.x
pip install "image_match[es7] @ git+https://github.com/maksym-lukianenko/image-match.git@master"

# Elasticsearch 8.x
pip install "image_match[es8] @ git+https://github.com/maksym-lukianenko/image-match.git@master"
```

---

## Quick start

### Generate a signature

```python
from image_match.goldberg import ImageSignature

gis = ImageSignature()
sig = gis.generate_signature('https://example.com/image.jpg')
```

### Store and search with Elasticsearch 7.x

```python
from elasticsearch import Elasticsearch
from image_match.elasticsearch_driver_es7 import SignatureES7

es = Elasticsearch()
ses = SignatureES7(es=es, index='images')

ses.add_image('https://example.com/image.jpg')
results = ses.search_image('https://example.com/similar.jpg')
# [{'path': '...', 'dist': 0.12, 'score': 0.88, 'id': '...'}]
```

### Store and search with Elasticsearch 8.x

```python
from elasticsearch import Elasticsearch
from image_match.elasticsearch_driver_es8 import SignatureES8

es = Elasticsearch(['http://localhost:9200'])
ses = SignatureES8(es=es, index='images')

ses.add_image('https://example.com/image.jpg')
results = ses.search_image('https://example.com/similar.jpg')
```

### Add images from file or bytestream

```python
# From file path
ses.add_image('path/to/image.jpg')

# From bytestream
with open('image.jpg', 'rb') as f:
    ses.add_image('my-image-key', img=f.read(), bytestream=True)

# With metadata
ses.add_image('path/to/image.jpg', metadata={'tenant_id': 'acme'})
```

### Search with metadata filter

```python
# ES 7.x
results = ses.search_image(
    'path/to/query.jpg',
    pre_filter={"term": {"image.metadata.tenant_id": "acme"}}
)

# ES 8.x
results = ses.search_image(
    'path/to/query.jpg',
    pre_filter={"term": {"metadata.tenant_id": "acme"}}
)
```

### Backward compatibility

Code using the old `SignatureES` class continues to work with a deprecation warning:

```python
from image_match.elasticsearch_driver import SignatureES  # DeprecationWarning
ses = SignatureES(es=es, index='images')  # delegates to SignatureES7
```

---

## Running tests locally

Requires Docker.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[es7,test]"

make test-es7   # runs ES 7.x suite
make test-es8   # runs ES 8.x suite
make test       # runs both
```

---

## CI

GitHub Actions runs both ES7 and ES8 test suites on every push and pull request to `master`.
