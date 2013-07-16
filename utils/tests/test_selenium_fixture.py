import time

import pytest

from pages.page import Page

@pytest.mark.nondestructive
def test_selenium(selenium):
    with selenium('http://www.redhat.com', Page) as page:
        assert 'redhat.com' in page.selenium.current_url.lower()

    with selenium('http://www.google.com', Page) as page:
        assert 'google.com' in page.selenium.current_url.lower()

