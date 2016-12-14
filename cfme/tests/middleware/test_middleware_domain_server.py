import pytest
from cfme.middleware.domain import MiddlewareDomain
from cfme.middleware.provider import get_random_list
from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.middleware.server_group import MiddlewareServerGroup
from cfme.middleware.server import MiddlewareServer
from cfme.web_ui import flash
from utils import testgen
from utils.version import current_version
from server_methods import verify_server_running, verify_server_stopped
from server_methods import get_servers_set, verify_server_suspended
from server_methods import get_domain_server
from server_methods import verify_server_starting, verify_server_stopping

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate([HawkularProvider], scope="function")


@pytest.yield_fixture(scope="function")
def domain_server(provider):
    server = get_domain_server(provider)
    yield server
    # make sure server is resumed just in case, if after test server is suspended
    server.resume_server()
    # resume does not start stopped server
    # make sure server is started after test execution
    server.start_server()


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


@pytest.mark.smoke
def test_domain_server_suspend_resume(provider, domain_server):
    """Tests domain mode server suspend/resume operation on UI

    Steps:
        * Invokes 'Suspend Server' toolbar operation
        * Checks that server status is not running in UI, in DB and in MGMT.
        * Invokes 'Resume Server' toolbar operation
        * Waits for some time
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    verify_server_running(provider, domain_server)
    domain_server.suspend_server()
    flash.assert_success_message('Suspend initiated for selected server(s)')
    verify_server_suspended(provider, domain_server)
    domain_server.resume_server()
    flash.assert_success_message('Resume initiated for selected server(s)')
    verify_server_running(provider, domain_server)


def test_domain_server_reload(provider, domain_server):
    """Tests domain mode server reload operation on UI

    Steps:
        * Invokes 'Reload Server' toolbar operation
        * Waits for some time
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    verify_server_running(provider, domain_server)
    domain_server.reload_server()
    flash.assert_success_message('Reload initiated for selected server(s)')
    verify_server_starting(provider, domain_server)
    verify_server_running(provider, domain_server)


def test_domain_server_stop_start(provider, domain_server):
    """Tests domain mode server stop/start operation on UI

    Steps:
        * Invokes 'Stop Server' toolbar operation
        * Checks that server status is stopped in UI, in DB and in MGMT.
        * Invokes 'Start Server' toolbar operation
        * Waits for some time
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    verify_server_running(provider, domain_server)
    domain_server.stop_server()
    flash.assert_success_message('Stop initiated for selected server(s)')
    verify_server_stopping(provider, domain_server)
    verify_server_stopped(provider, domain_server)
    domain_server.start_server()
    flash.assert_success_message('Start initiated for selected server(s)')
    verify_server_starting(provider, domain_server)
    verify_server_running(provider, domain_server)


def test_domain_server_restart(provider, domain_server):
    """Tests domain mode server restart operation on UI

    Steps:
        * Invokes 'Restart Server' toolbar operation
        * Waits for some time
        * Checks that server status is running in UI, in DB and in MGMT.
    """
    verify_server_running(provider, domain_server)
    domain_server.restart_server()
    flash.assert_success_message('Restart initiated for selected server(s)')
    verify_server_starting(provider, domain_server)
    verify_server_running(provider, domain_server)


def test_domain_server_kill(provider, domain_server):
    """Tests domain mode server kill operation on UI

    Steps:
        * Invokes 'Kill Server' toolbar operation
        * Checks that server status is stopped in UI, in DB and in MGMT.
    """
    verify_server_running(provider, domain_server)
    domain_server.kill_server()
    flash.assert_success_message('Kill initiated for selected server(s)')
    verify_server_stopping(provider, domain_server)
    verify_server_stopped(provider, domain_server)
