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


def test_index_refresh(ses):
    ses.add_image('test1.jpg')
    r = ses.search_image('test1.jpg')
    assert len(r) == 1


def test_lookup_from_file(ses):
    ses.add_image('test1.jpg')
    r = ses.search_image('test1.jpg')
    assert len(r) == 1
    assert r[0]['path'] == 'test1.jpg'
    assert 'dist' in r[0]
    assert 'id' in r[0]
    assert 'score' in r[0]


def test_lookup_from_url(ses):
    ses.add_image('test1.jpg')
    r = ses.search_image(test_img_url1)
    assert len(r) == 1
    assert r[0]['path'] == 'test1.jpg'


def test_lookup_from_bytestream(ses):
    ses.add_image('test1.jpg')
    with open('test1.jpg', 'rb') as f:
        r = ses.search_image(f.read(), bytestream=True)
    assert len(r) == 1
    assert r[0]['path'] == 'test1.jpg'


def test_lookup_with_cutoff(ses):
    ses.add_image('test2.jpg')
    ses.distance_cutoff = 0.01
    r = ses.search_image('test1.jpg')
    assert len(r) == 0


def test_dist_is_close_to_zero_for_identical_image(ses):
    ses.add_image('test1.jpg')
    r = ses.search_image('test1.jpg')
    assert len(r) == 1
    assert r[0]['dist'] < 0.05


def test_similar_images_found_within_default_cutoff(ses):
    # test2.jpg is a 3-degree rotation of test1.jpg, distance ~0.28
    ses.add_image('test2.jpg')
    r = ses.search_image('test1.jpg')
    assert len(r) == 1
    assert r[0]['dist'] < 0.45
    assert r[0]['dist'] > 0.01


def test_all_orientations(ses):
    from PIL import Image
    Image.open('test1.jpg').rotate(90, expand=True).save('rotated_test1.jpg')
    ses.add_image('test1.jpg')
    r = ses.search_image('rotated_test1.jpg', all_orientations=True)
    assert len(r) == 1
    assert r[0]['path'] == 'test1.jpg'
    assert r[0]['dist'] < 0.05


def test_add_image_with_metadata(ses):
    metadata = {'some_info': {'test': 'ok!'}}
    ses.add_image('test1.jpg', metadata=metadata)
    r = ses.search_image('test1.jpg')
    assert r[0]['metadata'] == metadata
    assert 'path' in r[0]
    assert 'dist' in r[0]
    assert 'id' in r[0]


def test_lookup_with_filter_by_metadata(ses):
    ses.add_image('test1.jpg', metadata={'tenant_id': 'foo'})
    ses.add_image('test2.jpg', metadata={'tenant_id': 'bar'})

    r = ses.search_image(
        'test1.jpg',
        pre_filter=Filter(must=[FieldCondition(key='metadata.tenant_id', match=MatchValue(value='foo'))]),
    )
    assert len(r) == 1
    assert r[0]['metadata']['tenant_id'] == 'foo'

    r = ses.search_image(
        'test1.jpg',
        pre_filter=Filter(must=[FieldCondition(key='metadata.tenant_id', match=MatchValue(value='bar'))]),
    )
    assert len(r) == 1
    assert r[0]['metadata']['tenant_id'] == 'bar'

    r = ses.search_image(
        'test1.jpg',
        pre_filter=Filter(must=[FieldCondition(key='metadata.tenant_id', match=MatchValue(value='nonexistent'))]),
    )
    assert len(r) == 0


def test_delete_image(ses):
    ses.add_image('test1.jpg')
    ses.delete_image('test1.jpg')
    r = ses.search_image('test1.jpg')
    assert len(r) == 0


def test_duplicate(ses):
    ses.add_image('test1.jpg')
    ses.add_image('test1.jpg')
    r = ses.search_image('test1.jpg')
    assert len(r) == 2
    assert all(m['path'] == 'test1.jpg' for m in r)


def test_duplicate_removal(ses):
    for _ in range(5):
        ses.add_image('test1.jpg')
    r = ses.search_image('test1.jpg')
    assert len(r) == 5
    ses.delete_duplicates('test1.jpg')
    r = ses.search_image('test1.jpg')
    assert len(r) == 1
