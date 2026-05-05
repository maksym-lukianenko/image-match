import hashlib
import os

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from image_match.elasticsearch_driver_qdrant import SignatureQdrant
from tests.conftest import TEST_IMG_URL1 as test_img_url1
from tests.conftest import TEST_IMG_URL2 as test_img_url2

COLLECTION_NAME = 'test_qdrant_{}'.format(hashlib.md5(os.urandom(128)).hexdigest()[:12])
QDRANT_URL = 'http://localhost:6333'


@pytest.fixture(scope='function')
def qdrant_client():
    return QdrantClient(url=QDRANT_URL)


@pytest.fixture(scope='function')
def ses(qdrant_client):
    sq = SignatureQdrant(client=qdrant_client, collection_name=COLLECTION_NAME)
    sq.ensure_collection()
    yield sq
    qdrant_client.delete_collection(COLLECTION_NAME)


def test_qdrant_running(qdrant_client):
    info = qdrant_client.get_collections()
    assert info is not None


def test_ensure_collection_creates_collection(qdrant_client):
    name = 'test_ensure_{}'.format(hashlib.md5(os.urandom(64)).hexdigest()[:8])
    sq = SignatureQdrant(client=qdrant_client, collection_name=name)
    sq.ensure_collection()
    collections = {c.name for c in qdrant_client.get_collections().collections}
    assert name in collections
    qdrant_client.delete_collection(name)


def test_ensure_collection_is_idempotent(qdrant_client):
    name = 'test_idempotent_{}'.format(hashlib.md5(os.urandom(64)).hexdigest()[:8])
    sq = SignatureQdrant(client=qdrant_client, collection_name=name)
    sq.ensure_collection()
    sq.ensure_collection()  # must not raise
    qdrant_client.delete_collection(name)


def test_add_image_by_path(ses):
    ses.add_image('test1.jpg')


def test_add_image_by_url(ses):
    ses.add_image(test_img_url1)


def test_add_image_as_bytestream(ses):
    with open('test1.jpg', 'rb') as f:
        ses.add_image('bytestream_test', img=f.read(), bytestream=True)


def test_add_image_with_different_name(ses):
    ses.add_image('custom_name_test', img='test1.jpg', bytestream=False)
