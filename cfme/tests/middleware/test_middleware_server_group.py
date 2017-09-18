import pytest

from cfme.middleware.domain import MiddlewareDomain
from cfme.middleware.provider import get_random_list
from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.middleware.server_group import MiddlewareServerGroup
from cfme.utils import testgen
from cfme.utils.version import current_version
from server_group_methods import (
    verify_server_group_stopped, verify_server_group_running,
    verify_server_group_suspended,
    check_group_deployment_enabled,
    check_group_deployment_disabled,
    check_group_deployment_content
)
from deployment_methods import deploy
from deployment_methods import RESOURCE_JAR_NAME, RESOURCE_WAR_NAME
from deployment_methods import WAR_EXT, RESOURCE_WAR_NAME_NEW
from deployment_methods import RESOURCE_WAR_CONTENT, RESOURCE_WAR_CONTENT_NEW
from server_methods import get_domain_container_server

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate([HawkularProvider], scope="function")

ITEMS_LIMIT = 1  # when we have big list, limit number of items to test


@pytest.yield_fixture(scope="function")
def main_server_group(provider):
    domain_list = MiddlewareDomain.domains_in_db(provider=provider, strict=False)
    assert domain_list, "Domain was not found in DB"
    domain = domain_list[0]
    server_group_list = MiddlewareServerGroup.server_groups_in_db(
        domain=domain, name="main-server-group", strict=False)
    assert server_group_list, "Server group was not found in DB"
    server_group = server_group_list[0]
    yield server_group
    # make sure server is resumed just in case, if after test server group is suspended
    server_group.resume_server_group()
    # resume does not start stopped server group
    # make sure server is started after test execution
    server_group.start_server_group()


def test_list_provider_server_groups(provider):
    """Tests server groups lists from current Provider between UI, DB and Management system

    Steps:
        * Get domains list from DB
        * Chooses one of domains
        * Get server groups list from UI of domain
        * Get server groups list from Database of domain
        * Get server groups list from Management system(Hawkular)
        * Get headers from UI
        * Compare headers from UI with expected headers list
        * Compare content of all the list [UI, Database, Management system]
    """
    domain_list = MiddlewareDomain.domains_in_db(provider=provider)
    for domain in get_random_list(domain_list, 1):
        ui_server_groups = get_server_group_set(
            MiddlewareServerGroup.server_groups(domain=domain))
        db_server_groups = get_server_group_set(
            MiddlewareServerGroup.server_groups_in_db(domain=domain))
        mgmt_server_groups = get_server_group_set(
            MiddlewareServerGroup.server_groups_in_mgmt(domain=domain))
        headers = MiddlewareServerGroup.headers(domain)
        headers_expected = ['Server Group Name', 'Feed', 'Domain Name', 'Profile']
        assert headers == headers_expected
        assert ui_server_groups == db_server_groups == mgmt_server_groups, \
            ("Lists of server groups mismatch! UI:{}, DB:{}, MGMT:{}"
             .format(ui_server_groups, db_server_groups, mgmt_server_groups))


def test_server_group_details(provider):
    """Tests server group details on UI

    Steps:
        * Get domains list from DB
        * Chooses one of domains
        * Get server groups list from DB
        * Chooses several server groups from list
        * Select each server group's details in UI, DB and MGMT
        * Compare selected server group UI details with CFME database and MGMT system
    """
    domain_list = MiddlewareDomain.domains_in_db(provider=provider, strict=False)
    for domain in get_random_list(domain_list, ITEMS_LIMIT):
        server_group_list = MiddlewareServerGroup.server_groups_in_db(domain=domain, strict=False)
        for server_group in get_random_list(server_group_list, 1):
            svgr_ui = server_group.server_group(method='ui')
            svgr_db = server_group.server_group(method='db')
            svgr_mgmt = server_group.server_group(method='mgmt')
            assert svgr_ui, "Server Group was not found in UI"
            assert svgr_db, "Server Group was not found in DB"
            assert svgr_mgmt, "Server Group was not found in MGMT system"
            assert svgr_ui.name == svgr_db.name == svgr_mgmt.name, \
                ("Server Group name does not match between UI:{}, DB:{}, MGMT:{}"
                 .format(svgr_ui.name, svgr_db.name, svgr_mgmt.name))
            svgr_db.validate_properties()
            svgr_mgmt.validate_properties()


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_server_group_restart(provider, main_server_group):
    """Tests domain server group restart operation on UI

    Steps:
        * Invokes 'Restart Server Group' toolbar operation
        * Waits for some time
        * Checks that all servers in that server group have status running in UI, in DB and in MGMT.
    """
    verify_server_group_running(provider, main_server_group)
    main_server_group.restart_server_group()
    verify_server_group_running(provider, main_server_group)


@pytest.mark.smoke
@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_server_group_suspend_resume(provider, main_server_group):
    """Tests domain mode server group suspend/resume operation on UI

    Steps:
        * Invokes 'Suspend Server Group' toolbar operation
        * Checks that server group's servers status is not running in UI, in DB and in MGMT.
        * Invokes 'Resume Server Group' toolbar operation
        * Waits for some time
        * Checks that server group's server status is running in UI, in DB and in MGMT.
    """
    verify_server_group_running(provider, main_server_group)
    main_server_group.suspend_server_group()
    verify_server_group_suspended(provider, main_server_group)
    main_server_group.resume_server_group()
    verify_server_group_running(provider, main_server_group)


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_server_group_reload(provider, main_server_group):
    """Tests domain mode server group reload operation on UI

    Steps:
        * Invokes 'Reload Server Group' toolbar operation
        * Waits for some time
        * Checks that server group's server status is running in UI, in DB and in MGMT.
    """
    verify_server_group_running(provider, main_server_group)
    main_server_group.reload_server_group()
    verify_server_group_running(provider, main_server_group)


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_server_group_stop_start(provider, main_server_group):
    """Tests domain mode server group stop/start operation on UI

    Steps:
        * Invokes 'Stop Server Group' toolbar operation
        * Checks that server status is stopped in UI, in DB and in MGMT.
        * Invokes 'Start Server Group' toolbar operation
        * Waits for some time
        * Checks that server group's server status is running in UI, in DB and in MGMT.
    """
    verify_server_group_running(provider, main_server_group)
    main_server_group.stop_server_group()
    verify_server_group_stopped(provider, main_server_group)
    main_server_group.start_server_group()
    verify_server_group_running(provider, main_server_group)


@pytest.mark.parametrize("archive_name", [RESOURCE_WAR_NAME])
def test_deploy(provider, main_server_group, archive_name):
    """Tests Deployment of provided archive into main_server_group

    Steps:
        * Get server groups list from UI
        * Chooses main_server_group from list
        * Invokes 'Add Deployment' toolbar operation
        * Selects "war" file to upload.
        * Chose random Runtime Name.
        * Checks that notification message is shown.
        * Refreshes the provider.
        * Verifies that deployment is shown in list of all servers from main_server_group
        * and is Enabled.
    """
    runtime_name = deploy(provider, main_server_group, archive_name)
    check_group_deployment_enabled(provider, main_server_group, runtime_name)


@pytest.mark.parametrize("archive_name", [RESOURCE_JAR_NAME])
def test_deploy_disabled(provider, main_server_group, archive_name):
    """Tests Deployment of provided archive into main_server_group as Disabled

    Steps:
        * Get server groups list from UI
        * Chooses main_server_group from lmain_server_groupist
        * Invokes 'Add Deployment' toolbar operation
        * Selects "war" file to upload.
        * Chose random Runtime Name.
        * Check "No" for "Enable Deployment".
        * Checks that notification message is shown.
        * Refreshes the provider.
        * Verifies that deployment is shown in list of all servers from main_server_group
        * and is Enabled.
    """
    runtime_name = deploy(provider, main_server_group, archive_name, enabled=False)
    check_group_deployment_disabled(provider, main_server_group, runtime_name)


def test_redeploy_overwrite(provider, main_server_group):
    """Tests Force Redeployment of already deployed archive into main_server_group

    Steps:
        * Get server groups list from UI
        * Chooses main_server_group from list
        * Deploys some deployment archive into main_server_group.
        * Refreshes the provider.
        * Lists all deployments on main_server_group's servers.
        * Verified the recently deployed archive's status is Enabled.
        * Deploys newer version of the same deployment archive into main_server_group,
          check to overwrite deployment.
        * Refreshes the provider.
        * Lists all deployments on main_server_group's servers.
        * Verified the recently deployed archive's status is Enabled.
    """
    runtime_name = deploy(provider, main_server_group, RESOURCE_WAR_NAME)
    check_group_deployment_enabled(provider, main_server_group, runtime_name)
    check_group_deployment_content(provider, main_server_group, runtime_name.replace(WAR_EXT, ''),
                             RESOURCE_WAR_CONTENT)
    deploy(provider, main_server_group, RESOURCE_WAR_NAME_NEW, runtime_name=runtime_name,
           overwrite=True)
    check_group_deployment_enabled(provider, main_server_group, runtime_name)
    check_group_deployment_content(provider, main_server_group, runtime_name.replace(WAR_EXT, ''),
                             RESOURCE_WAR_CONTENT_NEW)


@pytest.mark.uncollect
def test_container_server_group_immutability(provider):
    """Tests container based EAP server group immutability on UI

    Steps:
        * Select container based EAP domain server details in UI
        * Click on Relationships Middleware Server Group
        * Verify that all menu items are disabled and server group is immutable
    """
    server = get_domain_container_server(provider)
    srv_ui = server.server(method='ui')
    assert srv_ui, "Server was not found in UI"
    srv_group_ui = srv_ui.server_group(method='ui')
    assert srv_group_ui.is_immutable(), "Server Group in container should be immutable"


def get_server_group_set(server_groups):
    """
    Return the set of server groups which contains only necessary fields,
    such as 'feed', 'domain.name', 'name' and 'profile'
    """
    return set((server_group.feed, server_group.domain.name, server_group.name,
                server_group.profile)
               for server_group in server_groups)
