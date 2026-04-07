from urllib.request import urlretrieve

import pytest
from numpy import array_equal, ndarray

from image_match.goldberg import CorruptImageError, ImageSignature

test_img_url = 'https://picsum.photos/seed/mona/400/600.jpg'
test_diff_img_url = 'https://picsum.photos/seed/diff/400/600.jpg'


@pytest.fixture(scope='session', autouse=True)
def download_test_image(tmp_path_factory):
    dest = tmp_path_factory.mktemp('images') / 'test.jpg'
    urlretrieve(test_img_url, str(dest))
    return str(dest)


def test_load_from_url():
    gis = ImageSignature()
    sig = gis.generate_signature(test_img_url)
    assert type(sig) is ndarray
    assert sig.shape == (648,)


def test_load_from_file(download_test_image):
    gis = ImageSignature()
    sig = gis.generate_signature(download_test_image)
    assert type(sig) is ndarray
    assert sig.shape == (648,)


def test_load_from_stream(download_test_image):
    gis = ImageSignature()
    with open(download_test_image, 'rb') as f:
        sig = gis.generate_signature(f.read(), bytestream=True)
        assert type(sig) is ndarray
        assert sig.shape == (648,)


def test_load_from_corrupt_stream():
    gis = ImageSignature()
    with pytest.raises(CorruptImageError):
        gis.generate_signature(b'corrupt', bytestream=True)


def test_all_inputs_same_sig(download_test_image):
    gis = ImageSignature()
    sig1 = gis.generate_signature(test_img_url)
    sig2 = gis.generate_signature(download_test_image)
    with open(download_test_image, 'rb') as f:
        sig3 = gis.generate_signature(f.read(), bytestream=True)

    assert array_equal(sig1, sig2)
    assert array_equal(sig2, sig3)


def test_identity(download_test_image):
    gis = ImageSignature()
    sig = gis.generate_signature(download_test_image)
    dist = gis.normalized_distance(sig, sig)
    assert dist == 0.0


def test_difference(download_test_image):
    gis = ImageSignature()
    sig1 = gis.generate_signature(download_test_image)
    sig2 = gis.generate_signature(test_diff_img_url)
    dist = gis.normalized_distance(sig1, sig2)
    assert dist > 0.0
