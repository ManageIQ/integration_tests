import pytest

from pages.page import Page
from unittestzero import Assert

pytestmark = pytest.mark.nondestructive


# Mock fixture to keep things relatively fast
def mock_fixture(home_page_logged_in):
    return home_page_logged_in


def test_selenium_fixture(selenium):
    # Test the mozwebqa base_url and a fixture
    with selenium(mock_fixture) as page:
        Assert.true(page.is_the_current_page)
        Assert.true(isinstance(page, Page))


def test_selenium_fixture_string(selenium):
    with selenium('cnf_about_pg') as page:
        Assert.true(page.is_the_current_page)
        Assert.true(isinstance(page, Page))
