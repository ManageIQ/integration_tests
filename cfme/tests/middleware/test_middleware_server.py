import pytest
from cfme.middleware import get_random_list
from cfme.middleware.domain import MiddlewareDomain
from cfme.middleware.server_group import MiddlewareServerGroup
from cfme.middleware.server import MiddlewareServer
from cfme.web_ui import flash
from utils import testgen
from utils.version import current_version
from utils.wait import wait_for
from deployment_methods import get_server
from deployment_methods import EAP_PRODUCT_NAME, HAWKULAR_PRODUCT_NAME

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")


@pytest.yield_fixture(scope="function")
def server(provider):
    server = get_server(provider, EAP_PRODUCT_NAME)
    yield server
    server.restart_server()


def test_list_servers():
    """Tests servers lists between UI, DB and Management system.

    Steps:
        * Get servers list from UI
        * Get servers list from Database
        * Get headers from UI
        * Compare headers from UI with expected headers list
        * Compare content of all the list [UI, Database, Management system]
    """
    ui_servers = get_servers_set(MiddlewareServer.servers())
    db_servers = get_servers_set(MiddlewareServer.servers_in_db())
    mgmt_servers = get_servers_set(MiddlewareServer.servers_in_mgmt())
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
    ui_servers = get_servers_set(MiddlewareServer.servers(provider=provider))
    db_servers = get_servers_set(MiddlewareServer.servers_in_db(provider=provider))
    mgmt_servers = get_servers_set(MiddlewareServer.servers_in_mgmt(provider=provider))
    assert ui_servers == db_servers == mgmt_servers, \
        ("Lists of servers mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_servers, db_servers, mgmt_servers))


def test_list_server_group_servers(provider):
    """Tests servers lists from server groups of domain and checks values
    between UI, DB and Management system

    Steps:
        * Get domains list from UI of provider
        * Chooses one of domains
        * Get server groups list from UI of domain
        * Get servers list from UI of each server group
        * Get servers list from Database of each server group
        * @TODO add support of checking in MGMT
        * Compare content of all the list [UI, Database]
    """
    domain_list = MiddlewareDomain.domains(provider=provider)
    for domain in get_random_list(domain_list, 1):
        server_groups = MiddlewareServerGroup.server_groups(domain=domain)
        for server_group in server_groups:
            ui_servers = get_servers_set(MiddlewareServer.servers(server_group=server_group))
            db_servers = get_servers_set(MiddlewareServer.servers_in_db(server_group=server_group))
            assert ui_servers == db_servers, \
                ("Lists of servers mismatch! UI:{}, DB:{}"
                 .format(ui_servers, db_servers))


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


def test_server_reload(provider, server):
    """Tests server reload operation on UI

    Steps:
        * Invokes 'Reload Server' toolbar operation
        * Checks that server status is not running in UI, in DB and in MGMT.
        * Waits for some time
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    check_server_running(server)
    server.reload_server()
    flash.assert_success_message('Reload initiated for selected server(s)')
    # enable when HWKINVENT-185 is fixed
    # check_server_stopped(server)
    check_server_running(server)


def test_hawkular_fail(provider):
    """Tests Hawkular server itself reload operation message on UI

    Steps:
        * Chooses Hawkular server.
        * Invokes all 'Power' toolbar operation
        * Checks that notification message is shown
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    server = get_server(provider, HAWKULAR_PRODUCT_NAME)
    server.reload_server()
    flash.assert_success_message('Not reloading the provider')
    check_server_running(server)
    server.stop_server()
    flash.assert_success_message('Not stopping the provider')
    check_server_running(server)
    server.shutdown_server()
    flash.assert_success_message('Not shutting down the provider')
    check_server_running(server)
    server.restart_server()
    flash.assert_success_message('Not restarting the provider')
    check_server_running(server)
    server.suspend_server()
    flash.assert_success_message('Not suspending the provider')
    check_server_running(server)
    server.resume_server()
    flash.assert_success_message('Not resuming the provider')
    check_server_running(server)


# enable when MiQ server start functionality is implemented
@pytest.mark.uncollect
def test_server_stop(provider, server):
    """Tests server stop operation on UI

    Steps:
        * Invokes 'Stop Server' toolbar operation
        * Checks that server status is not running in UI, in DB and in MGMT.
        * Invokes 'Start Server' toolbar operation
        * Waits for some time
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    check_server_running(server)
    server.stop_server()
    flash.assert_success_message('Stop initiated for selected server(s)')
    check_server_stopped(server)
    server.restart_server()
    check_server_running(server)


# enable when MiQ server start functionality is implemented
@pytest.mark.uncollect
def test_server_shutdown(provider, server):
    """Tests server gracefully shutdown operation on UI

    Steps:
        * Invokes 'Gracefully shutdown Server' toolbar operation
        * Checks that server status is not running in UI, in DB and in MGMT.
        * Invokes 'Start Server' toolbar operation
        * Waits for some time
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    check_server_running(server)
    server.shutdown_server()
    flash.assert_success_message('Shutdown initiated for selected server(s)')
    check_server_stopped(server)
    server.restart_server()
    check_server_running(server)


def test_server_restart(provider, server):
    """Tests server restart operation on UI

    Steps:
        * Invokes 'Restart Server' toolbar operation
        * Checks that server status is not running in UI, in DB and in MGMT.
        * Waits for some time
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    check_server_running(server)
    server.restart_server()
    flash.assert_success_message('Restart initiated for selected server(s)')
    check_server_running(server)


def test_server_suspend_resume(provider, server):
    """Tests server suspend/resume operation on UI

    Steps:
        * Invokes Suspend Server' toolbar operation
        * Checks that server status is not running in UI, in DB and in MGMT.
        * Invokes 'Resume Server' toolbar operation
        * Waits for some time
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    check_server_running(server)
    server.suspend_server()
    flash.assert_success_message('Suspend initiated for selected server(s)')
    server.resume_server()
    flash.assert_success_message('Resume initiated for selected server(s)')
    check_server_running(server)


def get_servers_set(servers):
    """
    Return the set of servers which contains only necessary fields,
    such as 'feed', 'provider.name' and 'name'
    @TODO add 'product' field once https://github.com/ManageIQ/manageiq/issues/10728 is fixed
    """
    return set((server.feed, server.provider.name, server.name)
               for server in servers)


def check_server_stopped(server):
    """
    @TODO find a way to check whether server is stopped, as status is always shown as running
    HWKINVENT-185
    """
    wait_for(lambda: not server.is_running(method='db') and not server.is_running(method='mgmt'),
            delay=10, num_sec=600, message='Server {} must be stopped'.format(server.name))


def check_server_running(server):
    wait_for(lambda: server.is_running(method='db') and server.is_running(method='mgmt'),
            delay=10, num_sec=600, message='Server {} must be running'.format(server.name))
