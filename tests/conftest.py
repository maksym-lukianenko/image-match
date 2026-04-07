from urllib.request import urlretrieve

import pytest

TEST_IMG_URL1 = 'https://picsum.photos/seed/mona/400/600.jpg'
TEST_IMG_URL2 = 'https://picsum.photos/seed/diff/400/600.jpg'


@pytest.fixture(scope='session', autouse=True)
def download_test_images():
    """Download test images once per session to the working directory."""
    urlretrieve(TEST_IMG_URL1, 'test1.jpg')
    urlretrieve(TEST_IMG_URL2, 'test2.jpg')
