from urllib.request import urlretrieve

import pytest
from PIL import Image

TEST_IMG_URL1 = 'https://picsum.photos/seed/mona/400/600.jpg'
TEST_IMG_URL2 = TEST_IMG_URL1  # kept for tests that use it as an ES path identifier


@pytest.fixture(scope='session', autouse=True)
def download_test_images():
    """Download test1.jpg and create test2.jpg as a slightly rotated variant.

    test2.jpg is derived from test1.jpg (3-degree rotation) so the pair has a
    known similarity distance of ~0.28, safely within the default distance
    cutoff (0.45) but well above the tight cutoff used in test_lookup_with_cutoff.
    """
    urlretrieve(TEST_IMG_URL1, 'test1.jpg')
    Image.open('test1.jpg').rotate(3, expand=False).save('test2.jpg')
