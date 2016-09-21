import pytest
from cfme.middleware import get_random_list
from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.middleware.server import MiddlewareServer
from cfme.middleware.datasource import MiddlewareDatasource
from cfme.middleware.deployment import MiddlewareDeployment
from cfme.middleware.domain import MiddlewareDomain
from cfme.middleware.server_group import MiddlewareServerGroup
from cfme.middleware.messaging import MiddlewareMessaging
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
                                        HawkularProvider, MiddlewareServer,
                                        MiddlewareDomain, MiddlewareMessaging])
def test_download_lists_base(filetype, objecttype):
    """ Download the items from base lists. """
    objecttype.download(filetype)


@pytest.mark.parametrize("filetype", ["txt", "csv"])
@pytest.mark.parametrize("objecttype", [MiddlewareDatasource, MiddlewareDeployment,
                                        MiddlewareServer, MiddlewareDomain,
                                        MiddlewareMessaging])
def test_download_lists_from_provider(provider, filetype, objecttype):
    """ Download the items from providers. """
    objecttype.download(filetype, provider=provider)


@pytest.mark.parametrize("filetype", ["txt", "csv"])
@pytest.mark.parametrize("objecttype", [MiddlewareDatasource, MiddlewareDeployment,
                                        MiddlewareMessaging])
def test_download_lists_from_provider_server(provider, filetype, objecttype):
    """ Download the items from provider's server. """
    objecttype.download(filetype, provider=provider,
                        server=get_random_server(provider=provider))


@pytest.mark.parametrize("filetype", ["txt", "csv"])
@pytest.mark.parametrize("objecttype", [MiddlewareServerGroup])
def test_download_lists_from_domain(provider, filetype, objecttype):
    """ Download the items from domains. """
    objecttype.download(filetype, domain=get_random_domain(provider))


@pytest.mark.parametrize("filetype", ["txt", "csv"])
@pytest.mark.parametrize("objecttype", [MiddlewareServer])
def test_download_lists_from_server_group(provider, filetype, objecttype):
    """ Download the items from domains. """
    objecttype.download(filetype, server_group=get_random_server_group(provider))


def verify_download(filetype):
    """ Verifies whether download was successful and no error was shown.
    Currently test framework does not allow to access download files.
    So leaving file content checks later.
    """
    flash.assert_no_errors()


def get_random_server(provider):
    servers = MiddlewareServer.servers(provider=provider)
    assert len(servers) > 0, "There is no server(s) available in UI"
    return get_random_list(servers, 1)[0]


def get_random_domain(provider):
    domains = MiddlewareDomain.domains(provider=provider)
    assert len(domains) > 0, "There is no domains(s) available in UI"
    return get_random_list(domains, 1)[0]


def get_random_server_group(provider):
    server_groups = MiddlewareServerGroup.server_groups(get_random_domain(provider))
    assert len(server_groups) > 0, "There is no server_groups(s) available in UI"
    return get_random_list(server_groups, 1)[0]
