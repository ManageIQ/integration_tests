import pytest
from cfme.middleware.server import MiddlewareServer
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.usefixtures('has_no_middleware_providers'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")


def test_list_servers(provider):
    """Tests servers lists between UI, DB and Management system

    Steps:
        * Get servers list from UI
        * Get servers list from Database
        * Get servers list from Management system(Hawkular)
        * Get headers from UI
        * Compare headers from UI with expected headers list
        * Compare content of all the list [UI, Database, Management system]
    """
    ui_servers = _get_servers_set(MiddlewareServer.servers())
    db_servers = _get_servers_set(MiddlewareServer.servers_in_db())
    mgmt_servers = _get_servers_set(MiddlewareServer.servers_in_mgmt(provider=provider))
    headers = MiddlewareServer.headers()
    headers_expected = ['Server Name', 'Product', 'Feed', 'Provider']
    assert headers == headers_expected
    assert ui_servers == db_servers == mgmt_servers, \
        ("Lists of servers mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_servers, db_servers, mgmt_servers))


def test_list_provider_servers(provider):
    """Tests servers lists from current Provider between UI, DB and Management system

    Steps:
        * Get servers list from UI of provider
        * Get servers list from Database of provider
        * Get servers list from Management system(Hawkular)
        * Compare content of all the list [UI, Database, Management system]
    """
    ui_servers = _get_servers_set(MiddlewareServer.servers(provider=provider))
    db_servers = _get_servers_set(MiddlewareServer.servers_in_db(provider=provider))
    mgmt_servers = _get_servers_set(MiddlewareServer.servers_in_mgmt(provider=provider))
    assert ui_servers == db_servers == mgmt_servers, \
        ("Lists of servers mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_servers, db_servers, mgmt_servers))


def _get_servers_set(servers):
    """
    Return the set of servers which contains only necessary fields,
    such as 'id', 'provider', 'name' and 'product'
    """
    return set((server.id, server.provider, server.name, server.product) for server in servers)
