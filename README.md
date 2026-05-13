# image-match

A Python library for finding approximate image matches from a corpus, backed by Elasticsearch.

This is a maintained fork of the original [image-match](https://github.com/edjo-labs/image-match) library (no longer maintained upstream).

Based on the paper [_An image signature for any kind of image_, Wong et al](http://www.cs.cmu.edu/~hcwong/Pdfs/icip02.ps).

**Note:** This algorithm finds nearly duplicate images (e.g. copyright violation detection). It is **not** intended to find conceptually similar images.

---

## Requirements

- Python 3.12+
- Elasticsearch 7.x or 8.x, **or** Qdrant 1.x

---

## Installation

Choose the extra matching your backend:

```bash
# Elasticsearch 7.x
pip install "image_match[es7] @ git+https://github.com/maksym-lukianenko/image-match.git@master"

# Elasticsearch 8.x
pip install "image_match[es8] @ git+https://github.com/maksym-lukianenko/image-match.git@master"

# Qdrant
pip install "image_match[qdrant] @ git+https://github.com/maksym-lukianenko/image-match.git@master"
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

### Store and search with Qdrant

```python
from qdrant_client import QdrantClient
from image_match.qdrant_driver import SignatureQdrant

client = QdrantClient(url='http://localhost:6333')
ses = SignatureQdrant(client=client, collection_name='images')

# Create the collection on first use (idempotent — safe to call every startup)
ses.ensure_collection()

ses.add_image('https://example.com/image.jpg')
results = ses.search_image('https://example.com/similar.jpg')
# [{'path': '...', 'dist': 0.12, 'score': 0.97, 'id': '...', 'metadata': None}]
```

`dist` is computed with the same `normalized_distance` formula as the ES drivers and is directly comparable across backends. `score` is Qdrant's raw cosine similarity and is **not** comparable with ES scores.

### Search with metadata filter (Qdrant)

Qdrant filters use `qdrant_client.models` objects, not ES-style dicts:

```python
from qdrant_client.models import FieldCondition, Filter, MatchValue

results = ses.search_image(
    'path/to/query.jpg',
    pre_filter=Filter(must=[FieldCondition(key='metadata.tenant_id', match=MatchValue(value='acme'))])
)
```

To make metadata filters efficient at scale, index the field when creating the collection:

```python
from qdrant_client.models import PayloadSchemaType

ses.ensure_collection(indexed_fields={'metadata.tenant_id': PayloadSchemaType.KEYWORD})
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

make test-es7     # runs ES 7.x suite
make test-es8     # runs ES 8.x suite
make test-qdrant  # runs Qdrant suite
make test         # runs all three
```

---

## CI

GitHub Actions runs the ES7, ES8, and Qdrant test suites on every push and pull request to `master`.
