import pytest
from cfme.middleware import get_random_list
from cfme.middleware.provider import HawkularProvider
from cfme.middleware.server import MiddlewareServer
from cfme.middleware.datasource import MiddlewareDatasource
from cfme.middleware.deployment import MiddlewareDeployment
import cfme.web_ui.flash as flash
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")


@pytest.mark.parametrize("filetype", ["txt", "csv"])
@pytest.mark.parametrize("objecttype", [MiddlewareDatasource, MiddlewareDeployment,
                                        HawkularProvider, MiddlewareServer])
def test_download_lists_base(filetype, objecttype):
    """ Download the items from base lists. """
    objecttype.download(filetype)


@pytest.mark.parametrize("filetype", ["txt", "csv"])
@pytest.mark.parametrize("objecttype", [MiddlewareDatasource, MiddlewareDeployment,
                                        MiddlewareServer])
def test_download_lists_from_provider(provider, filetype, objecttype):
    """ Download the items from providers. """
    objecttype.download(filetype, provider=provider)


@pytest.mark.parametrize("filetype", ["txt", "csv"])
@pytest.mark.parametrize("objecttype", [MiddlewareDatasource, MiddlewareDeployment])
def test_download_lists_from_provider_server(provider, filetype, objecttype):
    """ Download the items from provider's server. """
    objecttype.download(filetype, provider=provider,
                        server=_get_random_server(provider=provider))


def verify_download(filetype):
    """ Verifies whether download was successful and no error was shown.
    Currently test framework does not allow to access download files.
    So leaving file content checks later.
    """
    flash.assert_no_errors()


def _get_random_server(provider):
    servers = MiddlewareServer.servers(provider=provider)
    assert len(servers) > 0, "There is no server(s) available in UI"
    return get_random_list(servers, 1)[0]
