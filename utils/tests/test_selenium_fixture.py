import time

import pytest

from pages.page import Page

pytestmark = pytest.mark.nondestructive

def test_selenium_page(selenium):
    # Test an arbitrary URL and a Page object
    with selenium('http://www.google.com', Page) as page:
        assert 'google.com' in page.selenium.current_url.lower()

def test_selenium_fixture(mozwebqa, selenium):
    # Mock fixture to keep things as fast as possible
    def mock_fixture(home_page_logged_in):
        return home_page_logged_in

    # Test the mozwebqa base_url and a fixture
    with selenium(mozwebqa.base_url, mock_fixture) as page:
        assert page.is_the_current_page

