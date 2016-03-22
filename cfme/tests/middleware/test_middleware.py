import pytest
from utils.browser import ensure_browser_open
from cfme.login import login_admin
from cfme.fixtures import pytest_selenium as sel


@pytest.fixture
def webDriver(request):
    ensure_browser_open()
    login_admin()

    def closeSession():
        """ Place Holder for after-test action """
    request.addfinalizer(closeSession)

    return


def test_middleware():
    sel.force_navigate('middleware')
    assert sel.is_displayed_text('Middleware Managers')
