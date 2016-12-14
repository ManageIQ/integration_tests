import pytest
from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.middleware.server import MiddlewareServer
from cfme.middleware.datasource import MiddlewareDatasource
from cfme.middleware.deployment import MiddlewareDeployment
from cfme.middleware.domain import MiddlewareDomain
from cfme.middleware.server_group import MiddlewareServerGroup
from cfme.middleware.messaging import MiddlewareMessaging
from random_methods import get_random_object, get_random_domain
from random_methods import get_random_server, get_random_server_group
import cfme.web_ui.flash as flash
from utils import testgen
from utils import version
from utils.version import current_version

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate([HawkularProvider], scope="function")
FILETYPES = ["txt", "csv", "pdf"]


@pytest.mark.parametrize("filetype", FILETYPES)
@pytest.mark.parametrize("objecttype", [MiddlewareDatasource, MiddlewareDeployment,
                                        HawkularProvider, MiddlewareServer,
                                        MiddlewareDomain, MiddlewareMessaging])
@pytest.mark.uncollectif(lambda filetype: filetype in {"pdf"} and
                         current_version() == version.UPSTREAM)
def test_download_lists_base(filetype, objecttype):
    """ Download the items from base lists. """
    objecttype.download(filetype)


@pytest.mark.parametrize("filetype", FILETYPES)
@pytest.mark.parametrize("objecttype", [MiddlewareDatasource, MiddlewareDeployment,
                                        MiddlewareServer, MiddlewareDomain,
                                        MiddlewareMessaging])
@pytest.mark.uncollectif(lambda filetype: filetype in {"pdf"} and
                         current_version() == version.UPSTREAM)
def test_download_lists_from_provider(provider, filetype, objecttype):
    """ Download the items from providers. """
    objecttype.download(filetype, provider=provider)


@pytest.mark.parametrize("filetype", FILETYPES)
@pytest.mark.parametrize("objecttype", [MiddlewareDatasource, MiddlewareDeployment,
                                        MiddlewareMessaging])
@pytest.mark.uncollectif(lambda filetype: filetype in {"pdf"} and
                         current_version() == version.UPSTREAM)
def test_download_lists_from_provider_server(provider, filetype, objecttype):
    """ Download the items from provider's server. """
    objecttype.download(filetype, provider=provider,
                        server=get_random_server(provider=provider))


@pytest.mark.parametrize("filetype", FILETYPES)
@pytest.mark.parametrize("objecttype", [MiddlewareServerGroup])
@pytest.mark.uncollectif(lambda filetype: filetype in {"pdf"} and
                         current_version() == version.UPSTREAM)
def test_download_lists_from_domain(provider, filetype, objecttype):
    """ Download the items from domains. """
    objecttype.download(filetype, domain=get_random_domain(provider))


@pytest.mark.parametrize("filetype", FILETYPES)
@pytest.mark.parametrize("objecttype", [MiddlewareServer])
@pytest.mark.uncollectif(lambda filetype: filetype in {"pdf"} and
                         current_version() == version.UPSTREAM)
def test_download_lists_from_server_group(provider, filetype, objecttype):
    """ Download the items from domains. """
    objecttype.download(filetype, server_group=get_random_server_group(provider))


@pytest.mark.parametrize("objecttype", [MiddlewareDatasource, MiddlewareDeployment,
                                        HawkularProvider, MiddlewareServer,
                                        MiddlewareDomain, MiddlewareMessaging,
                                        MiddlewareServerGroup])
@pytest.mark.uncollectif(lambda: current_version() == version.UPSTREAM)
def test_download_summary(provider, objecttype):
    """ Download the summary page in PDF format """
    get_random_object(provider, objecttype).download_summary()


def verify_download(filetype):
    """ Verifies whether download was successful and no error was shown.
    Currently test framework does not allow to access download files.
    So leaving file content checks later.
    """
    flash.assert_no_errors()
