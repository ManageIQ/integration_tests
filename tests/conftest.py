# pylint: disable=E1101
import pytest

@pytest.fixture
def maximized(mozwebqa):
    '''Maximizes the browser window'''
    mozwebqa.selenium.maximize_window()
    return True

