import pytest

@pytest.fixture
def baseurl(fixtureconf, mozwebqa):
    """Override mozwebqa's baseurl for an individual test

    Put this fixture before other fixtures to ensure it takes effect

    """
    mozwebqa.base_url = fixtureconf['base_url']
