import pytest
from cfme.middleware import get_random_list
from cfme.middleware.server import MiddlewareServer
from utils import testgen
from utils.version import current_version
from cfme.web_ui import flash
from utils.wait import wait_for

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")


def test_list_servers():
    """Tests servers lists between UI, DB and Management system.

    Steps:
        * Get servers list from UI
        * Get servers list from Database
        * Get headers from UI
        * Compare headers from UI with expected headers list
        * Compare content of all the list [UI, Database, Management system]
    """
    ui_servers = _get_servers_set(MiddlewareServer.servers())
    db_servers = _get_servers_set(MiddlewareServer.servers_in_db())
    mgmt_servers = _get_servers_set(MiddlewareServer.servers_in_mgmt())
    headers = MiddlewareServer.headers()
    headers_expected = ['Server Name', 'Product', 'Host Name', 'Feed', 'Provider']
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


def test_server_details(provider):
    """Tests server details on UI

    Steps:
        * Get servers list from UI
        * Select each server details in UI
        * Compare selected server UI details with CFME database and MGMT system
    """
    server_list = MiddlewareServer.servers(provider=provider)
    for server in get_random_list(server_list, 1):
        srv_ui = server.server(method='ui')
        srv_db = server.server(method='db')
        srv_mgmt = srv_ui.server(method='mgmt')
        assert srv_ui, "Server was not found in UI"
        assert srv_db, "Server was not found in DB"
        assert srv_mgmt, "Server was not found in MGMT system"
        assert srv_ui.name == srv_db.name == srv_mgmt.name, \
            ("server name does not match between UI:{}, DB:{}, MGMT:{}"
             .format(srv_ui.name, srv_db.name, srv_mgmt.name))
        srv_db.validate_properties()
        srv_mgmt.validate_properties()


def test_server_reload(provider):
    """Tests server reload operation on UI

    Steps:
        * Get servers list from UI
        * Chooses Wildfly server from list
        * Invokes 'Reload Server' toolbar operation
        * Checks that server status is not running in UI, in DB and in MGMT.
        * Waits for some time
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    server_list = MiddlewareServer.servers(provider=provider)
    for _server in server_list:
        if _server.product != 'Hawkular':
            server = _server
            break
    assert server, 'Wildfly server was not found in servers list'
    _check_server_running(server)
    server.reload_server()
    flash.assert_success_message('Reload initiated for selected server(s)')
    # enable when HWKINVENT-185 is fixed
    # _check_server_stopped(server)
    _check_server_running(server)


def test_hawkular_reload(provider):
    """Tests Hawkular server itself reload operation message on UI

    Steps:
        * Get servers list from UI
        * Chooses Hawkular server from list
        * Invokes 'Reload Server' toolbar operation
        * Checks that notification message is shown
        * Checks that server status is running in UI, in DB and in MGMT.
        * Invokes 'Stop Server' toolbar operation
        * Checks that notification message is shown
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    server_list = MiddlewareServer.servers(provider=provider)
    for _server in server_list:
        if _server.product == 'Hawkular':
            server = _server
            break
    assert server, 'Hawkular server was not found in servers list'
    server.reload_server()
    flash.assert_success_message('Not reloading Hawkular server')
    _check_server_running(server)
    server.stop_server()
    flash.assert_success_message('Not stopping Hawkular server')
    _check_server_running(server)


# enable when HWKINVENT-185 is fixed
@pytest.mark.uncollect
def test_server_stop(provider):
    """Tests server reload operation on UI

    Steps:
        * Get servers list from UI
        * Chooses Wildfly server from list
        * Invokes 'Stop Server' toolbar operation
        * Checks that server status is not running in UI, in DB and in MGMT.
        * Invokes 'Start Server' toolbar operation
        * Waits for some time
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    server_list = MiddlewareServer.servers(provider=provider)
    for _server in server_list:
        if _server.product != 'Hawkular':
            server = _server
            break
    assert server, 'Wildfly server was not found in servers list'
    _check_server_running(server)
    server.stop_server()
    flash.assert_success_message('Stop initiated for selected server(s)')
    _check_server_stopped(server)
    server.start_server()
    _check_server_running(server)


def _get_servers_set(servers):
    """
    Return the set of servers which contains only necessary fields,
    such as 'feed', 'provider.name', 'name' and 'product'
    """
    return set((server.feed, server.provider.name, server.name, server.product)
               for server in servers)


def _check_server_stopped(server):
    wait_for(lambda: not server.is_running(method='db') and not server.is_running(method='mgmt'),
            delay=10, num_sec=600, message='Server {} must be stopped'.format(server.name))


def _check_server_running(server):
    wait_for(lambda: server.is_running(method='db') and server.is_running(method='mgmt'),
            delay=10, num_sec=600, message='Server {} must be running'.format(server.name))
