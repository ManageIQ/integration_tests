import pytest
from cfme.middleware.server import MiddlewareServer
from cfme.web_ui import flash
from utils import testgen
from utils.version import current_version
from server_methods import verify_server_running, verify_server_stopped
from server_methods import get_servers_set, verify_server_suspended
from server_methods import get_eap_server, get_hawkular_server
from server_methods import verify_server_starting, verify_server_stopping

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")


@pytest.yield_fixture(scope="function")
def server(provider):
    server = get_eap_server(provider)
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


def test_server_details(provider):
    """Tests server details on UI

    Steps:
        * Select Hawkular server details in UI
        * Compare selected server UI details with CFME database and MGMT system
    """
    server = get_hawkular_server(provider)
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


# disabled as Hawkular server does not have 'Power' toolbar operation
@pytest.mark.uncollect
def test_hawkular_fail(provider):
    """Tests Hawkular server itself reload operation message on UI

    Steps:
        * Chooses Hawkular server.
        * Invokes all 'Power' toolbar operation
        * Checks that notification message is shown
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    server = get_hawkular_server(provider)
    server.reload_server()
    flash.assert_success_message('Not reloading the provider')
    verify_server_running(provider, server)
    server.stop_server()
    flash.assert_success_message('Not stopping the provider')
    verify_server_running(provider, server)
    server.shutdown_server()
    flash.assert_success_message('Not shutting down the provider')
    verify_server_running(provider, server)
    server.restart_server()
    flash.assert_success_message('Not restarting the provider')
    verify_server_running(provider, server)
    server.suspend_server()
    flash.assert_success_message('Not suspending the provider')
    verify_server_running(provider, server)
    server.resume_server()
    flash.assert_success_message('Not resuming the provider')
    verify_server_running(provider, server)


def test_server_reload(provider, server):
    """Tests server reload operation on UI

    Steps:
        * Invokes 'Reload Server' toolbar operation
        * Checks that server status is not running in UI, in DB and in MGMT.
        * Waits for some time
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    verify_server_running(provider, server)
    server.reload_server()
    flash.assert_success_message('Reload initiated for selected server(s)')
    verify_server_running(provider, server)


# enable when MiQ server start functionality is implemented
@pytest.mark.uncollect
def test_server_stop(provider, server):
    """Tests server stop operation on UI

    Steps:
        * Invokes 'Stop Server' toolbar operation
        * Checks that server status is stopped in UI, in DB and in MGMT.
    """
    verify_server_running(provider, server)
    server.stop_server()
    flash.assert_success_message('Stop initiated for selected server(s)')
    verify_server_stopping(provider, server)
    verify_server_stopped(provider, server)
    server.start_server()
    flash.assert_success_message('Start initiated for selected server(s)')
    verify_server_starting(provider, server)
    verify_server_running(provider, server)


# enable when MiQ server start functionality is implemented
@pytest.mark.uncollect
def test_server_shutdown(provider, server):
    """Tests server gracefully shutdown operation on UI

    Steps:
        * Invokes 'Gracefully shutdown Server' toolbar operation
        * Checks that server status is stopped in UI, in DB and in MGMT.
    """
    verify_server_running(provider, server)
    server.shutdown_server()
    flash.assert_success_message('Shutdown initiated for selected server(s)')
    verify_server_stopping(provider, server)
    verify_server_stopped(provider, server)
    server.start_server()
    flash.assert_success_message('Start initiated for selected server(s)')
    verify_server_starting(provider, server)
    verify_server_running(provider, server)


def test_server_restart(provider, server):
    """Tests server restart operation on UI

    Steps:
        * Invokes 'Restart Server' toolbar operation
        * Checks that server status is not running in UI, in DB and in MGMT.
        * Waits for some time
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    verify_server_running(provider, server)
    server.restart_server()
    flash.assert_success_message('Restart initiated for selected server(s)')
    verify_server_running(provider, server)


def test_server_suspend_resume(provider, server):
    """Tests server suspend/resume operation on UI

    Steps:
        * Invokes Suspend Server' toolbar operation
        * Checks that server status is not running in UI, in DB and in MGMT.
        * Invokes 'Resume Server' toolbar operation
        * Waits for some time
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    verify_server_running(provider, server)
    server.suspend_server()
    flash.assert_success_message('Suspend initiated for selected server(s)')
    verify_server_suspended(provider, server)
    server.resume_server()
    flash.assert_success_message('Resume initiated for selected server(s)')
    verify_server_running(provider, server)
