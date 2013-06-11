import pytest

@pytest.fixture
def baseurl(request, mozwebqa):
    """Override mozwebqa's baseurl for an individual test

    Put this fixture before other fixtures to ensure it takes effect

    """
    mozwebqa.base_url = request.node._fixtureconf['base_url']
