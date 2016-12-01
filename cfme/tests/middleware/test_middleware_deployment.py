import pytest

import utils.error as error
from cfme.middleware import get_random_list
from cfme.middleware.deployment import MiddlewareDeployment
from utils import testgen
from utils.version import current_version
from deployment_methods import deploy, get_deployment_from_list
from deployment_methods import get_deployments_set
from deployment_methods import check_deployment_not_listed
from deployment_methods import check_deployment_disabled, check_deployment_enabled
from deployment_methods import RESOURCE_JAR_NAME, WAR_EXT
from deployment_methods import RESOURCE_WAR_NAME, RESOURCE_WAR_NAME_NEW
from deployment_methods import RESOURCE_WAR_CONTENT, RESOURCE_WAR_CONTENT_NEW
from deployment_methods import check_deployment_content, check_no_deployment_content
from server_methods import get_hawkular_server, get_eap_server

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")
ITEMS_LIMIT = 1  # when we have big list, limit number of items to test


def test_list_deployments(provider):
    """Tests deployments list between UI, DB and management system

    Steps:
        * Get deployments list from UI for whole Middleware
        * Get deployments list from Database for whole Middleware
        * Get deployments list from Management system  for whole Middleware
        * Verifies that UI list contains all DB entities
        * Verifies that UI list contains all MGMT entities
    """
    ui_deps = get_deployments_set(MiddlewareDeployment.deployments())
    db_deps = get_deployments_set(MiddlewareDeployment.deployments_in_db())
    mgmt_deps = get_deployments_set(MiddlewareDeployment.deployments_in_mgmt())
    assert ui_deps == db_deps, \
        ("Lists of deployments in UI does not contain the list in DB! UI:{}, DB:{}"
         .format(ui_deps, db_deps))
    assert ui_deps == mgmt_deps, \
        ("Lists of deployments in MGMT does not contain the list in DB! UI:{}, MGMT:{}"
         .format(ui_deps, mgmt_deps))


def test_list_server_deployments(provider):
    """Tests deployments list for Hawkular Local server

    Steps:
        * Get Hawkular Local server
        * Get deployments list from UI of server
        * Get deployments list from Database of server
        * Compares both lists [UI, Database]
    """
    server = get_hawkular_server(provider)
    ui_deps = get_deployments_set(MiddlewareDeployment.deployments(
        server=server))
    db_deps = get_deployments_set(MiddlewareDeployment.deployments_in_db(
        server=server))
    assert ui_deps == db_deps, \
        ("Lists of deployments mismatch! UI:{}, DB:{}".format(ui_deps, db_deps))


def test_list_provider_deployments(provider):
    """Tests deployments list from current Provider between UI, DB and Management system

    Steps:
        * Get deployments list from UI of provider
        * Get deployments list from Database  of provider
        * Get deployments list from Management system(Hawkular) of provider
        * Verifies that UI list contains all DB entities
        * Verifies that UI list contains all MGMT entities
    """
    ui_deps = get_deployments_set(MiddlewareDeployment.deployments(provider=provider))
    db_deps = get_deployments_set(MiddlewareDeployment.deployments_in_db(
        provider=provider))
    mgmt_deps = get_deployments_set(MiddlewareDeployment.deployments_in_mgmt(
        provider=provider))
    assert ui_deps == db_deps, \
        ("Lists of deployments in UI does not contain the list in DB! UI:{}, DB:{}"
         .format(ui_deps, db_deps))
    assert ui_deps == mgmt_deps, \
        ("Lists of deployments in MGMT does not contain the list in DB! UI:{}, MGMT:{}"
         .format(ui_deps, mgmt_deps))


def test_list_provider_server_deployments(provider):
    """Tests deployments list from current Provider for each server
    between UI, DB and Management system

    Steps:
        * Get Local server from UI of provider
        * Get deployments list for the server
        * Get deployments list from UI of provider, server
        * Get deployments list from Database of provider, server
        * Get deployments list from Database of provider, server
        * Get deployments list from Management system(Hawkular) of server
        * Compare size of all the list [UI, Database, Management system]
    """
    server = get_hawkular_server(provider)
    ui_deps = get_deployments_set(
        MiddlewareDeployment.deployments(provider=provider, server=server))
    db_deps = get_deployments_set(
        MiddlewareDeployment.deployments_in_db(provider=provider, server=server))
    mgmt_deps = get_deployments_set(
        MiddlewareDeployment.deployments_in_mgmt(provider=provider, server=server))
    assert ui_deps == db_deps == mgmt_deps, \
        ("Lists of deployments mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_deps, db_deps, mgmt_deps))


def test_deployment_details(provider):
    """Tests deployment details on UI

    Steps:
        * Get deployments list from DB
        * Select up to `ITEMS_LIMIT` deployments randomly
        * Compare selected deployment details with CFME database and UI
    """
    deps = MiddlewareDeployment.deployments_in_db(provider=provider,
                                               server=get_hawkular_server(provider))
    assert len(deps) > 0, "There is no deployment(s) available in DB"
    for dep in get_random_list(deps, ITEMS_LIMIT):
        dep_ui = dep.deployment(method='ui')
        dep_db = dep.deployment(method='db')
        assert dep_ui, "deployment was not found in UI"
        assert dep_db, "deployment was not found in DB"
        assert dep_ui.name == dep_db.name, \
            ("deployment name does not match between UI:{}, DB:{}"
             .format(dep_ui.name, dep_db.name))
        dep_db.validate_properties()


@pytest.mark.parametrize("archive_name", [RESOURCE_WAR_NAME, RESOURCE_JAR_NAME])
def test_deploy(provider, archive_name):
    """Tests Deployment of provided archive into EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Invokes 'Add Deployment' toolbar operation
        * Selects "war" file to upload.
        * Chose random Runtime Name.
        * Checks that notification message is shown.
        * Refreshes the provider.
        * Verifies that deployment is shown in list and is Enabled.
        * Selects deployment to show the details.
        * Verified details properties.
    """
    server = get_eap_server(provider)
    runtime_name = deploy(provider, server, archive_name)
    check_deployment_enabled(provider, server, runtime_name)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.validate_properties()


@pytest.mark.parametrize("archive_name", [RESOURCE_WAR_NAME, RESOURCE_JAR_NAME])
def test_deploy_disabled(provider, archive_name):
    """Tests Deployment of provided archive into EAP7 server as Disabled

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Invokes 'Add Deployment' toolbar operation
        * Selects "war" file to upload.
        * Chose random Runtime Name.
        * Check "No" for "Enable Deployment".
        * Checks that notification message is shown.
        * Refreshes the provider.
        * Verifies that deployment is shown in list and is Enabled.
        * Selects deployment to show the details.
        * Verified details properties.
    """
    server = get_eap_server(provider)
    runtime_name = deploy(provider, server, archive_name, enabled=False)
    check_deployment_disabled(provider, server, runtime_name)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.validate_properties()


@pytest.mark.parametrize("archive_name", [RESOURCE_WAR_NAME, RESOURCE_JAR_NAME])
def test_restart(provider, archive_name):
    """Tests Restart of archive from EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Deploys some deployment archive into server.
        * Select that deployment from deployments list.
        * Performs "Restart" toolbar operation on it.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently restarted archive is listed and is Enabled.
    """
    server = get_eap_server(provider)
    runtime_name = deploy(provider, server, archive_name)
    check_deployment_enabled(provider, server, runtime_name)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.restart()
    check_deployment_enabled(provider, server, runtime_name)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.validate_properties()


@pytest.mark.parametrize("archive_name", [RESOURCE_WAR_NAME, RESOURCE_JAR_NAME])
def test_undeploy(provider, archive_name):
    """Tests Undeployment of archive from EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Deploys some deployment archive into server.
        * Select that deployment from deployments list.
        * Performs "Undeploy" toolbar operation on it.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently undeployed archive is not listed anymore.
    """
    server = get_eap_server(provider)
    runtime_name = deploy(provider, server, archive_name)
    check_deployment_enabled(provider, server, runtime_name)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.undeploy()
    check_deployment_not_listed(provider, server, runtime_name)


@pytest.mark.parametrize("archive_name", [RESOURCE_WAR_NAME, RESOURCE_JAR_NAME])
def test_undeploy_disabled(provider, archive_name):
    """Tests Undeployment of disabled archive from EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Deploys some deployment archive into server.
        * Disabled the archive.
        * Select that deployment from deployments list.
        * Performs "Undeploy" toolbar operation on it.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently undeployed archive is not listed anymore.
    """
    server = get_eap_server(provider)
    runtime_name = deploy(provider, server, archive_name)
    check_deployment_enabled(provider, server, runtime_name)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.disable()
    check_deployment_disabled(provider, server, runtime_name)
    deployment.undeploy()
    check_deployment_not_listed(provider, server, runtime_name)


def test_redeploy_fail(provider):
    """Tests Redeployment of already deployed archive into EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Deploys some deployment archive into server.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently deployed archive's status is Enabled.
        * Deploys newer version of the same deployment archive into server.
        * Verify that exception is shown that archive already exists.
    """
    server = get_eap_server(provider)
    runtime_name = deploy(provider, server, RESOURCE_WAR_NAME)
    check_deployment_enabled(provider, server, runtime_name)
    with error.expected('Deployment "{}" already exists on this server.'.format(runtime_name)):
        deploy(provider, server, RESOURCE_WAR_NAME_NEW, runtime_name=runtime_name)


def test_redeploy_overwrite(provider):
    """Tests Force Redeployment of already deployed archive into EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Deploys some deployment archive into server.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently deployed archive's status is Enabled.
        * Deploys newer version of the same deployment archive into server,
          check to overwrite deployment.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently deployed archive's status is Enabled.
    """
    server = get_eap_server(provider)
    runtime_name = deploy(provider, server, RESOURCE_WAR_NAME)
    check_deployment_enabled(provider, server, runtime_name)
    deploy(provider, server, RESOURCE_WAR_NAME_NEW, runtime_name=runtime_name,
           overwrite=True)
    check_deployment_enabled(provider, server, runtime_name)


def test_redeploy_disabled(provider):
    """Tests Force Redeployment of already deployed and disabled archive into EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Deploys some deployment archive into server as Disabled.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently deployed archive's status is Disabled.
        * Deploys newer version of the same deployment archive into server as Disabled,
          check to overwrite existing archive.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently deployed archive's status is Disabled.
    """
    server = get_eap_server(provider)
    runtime_name = deploy(provider, server, RESOURCE_WAR_NAME, enabled=False)
    check_deployment_disabled(provider, server, runtime_name)
    deploy(provider, server, RESOURCE_WAR_NAME_NEW,
        runtime_name=runtime_name, enabled=False, overwrite=True)
    check_deployment_disabled(provider, server, runtime_name)


def test_redeploy_enable_disabled(provider):
    """Tests force Redeployment and enabling of already deployed and disabled archive into EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Deploys some deployment archive into server as Disabled.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently deployed archive's status is Disabled.
        * Deploys newer version of the same deployment archive into server as Enabled,
          check to overwrite existing deployment.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently deployed archive's status is Enabled.
    """
    server = get_eap_server(provider)
    runtime_name = deploy(provider, server, RESOURCE_WAR_NAME, enabled=False)
    check_deployment_disabled(provider, server, runtime_name)
    deploy(provider, server, RESOURCE_WAR_NAME_NEW, runtime_name=runtime_name,
           enabled=True, overwrite=True)
    check_deployment_enabled(provider, server, runtime_name)


def test_redeploy_disable_enabled(provider):
    """Tests force Redeployment and disabling of already deployed and enabled archive into EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Deploys some deployment archive into server as Enabled.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently deployed archive's status is Enabled.
        * Deploys newer version of the same deployment archive into server as Disabled,
          check to overwrite existing deployment.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently deployed archive's status is Disabled.
    """
    server = get_eap_server(provider)
    runtime_name = deploy(provider, server, RESOURCE_WAR_NAME, enabled=True)
    check_deployment_enabled(provider, server, runtime_name)
    deploy(provider, server, RESOURCE_WAR_NAME_NEW, runtime_name=runtime_name,
           enabled=False, overwrite=True)
    check_deployment_disabled(provider, server, runtime_name)


@pytest.mark.parametrize("archive_name", [RESOURCE_WAR_NAME, RESOURCE_JAR_NAME])
def test_disable_enable(provider, archive_name):
    """Tests Starting of stopped archive into EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Deploys some deployment archive into server.
        * Select that deployment from deployments list.
        * Performs "Disable" toolbar operation on it.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently disabled archive's status is Disabled.
        * Selects that archive from the list to load details.
        * Verifies that properties of deplyment's summary page and the status is Disabled.
        * Performs "Enable" toolbar operation on it.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently enabled archive's status is Enabled.
        * Selects that archive from the list to load details.
        * Verifies that properties of deplyment's summary page and the status is Enabled.
    """
    server = get_eap_server(provider)
    runtime_name = deploy(provider, server, archive_name)
    check_deployment_enabled(provider, server, runtime_name)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.disable()
    check_deployment_disabled(provider, server, runtime_name)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.validate_properties()
    deployment.enable()
    check_deployment_enabled(provider, server, runtime_name)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.validate_properties()


def test_disable_upgrade_enable(provider):
    """Tests upgrading disabled archive into EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Deploys some deployment archive into server.
        * Disable that archive.
        * Verified the recently disabled archive's status is Disabled.
        * Deploys newer version of the same deployment archive into server as Disabled.
        * Enables that archive.
        * Verified the recently enabled archive's status is Enabled.
        * Verify the content of new archive,
    """
    server = get_eap_server(provider)
    runtime_name = deploy(provider, server, RESOURCE_WAR_NAME)
    check_deployment_enabled(provider, server, runtime_name)
    check_deployment_content(provider, server, runtime_name.replace(WAR_EXT, ''),
                             RESOURCE_WAR_CONTENT)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.disable()
    check_deployment_disabled(provider, server, runtime_name)
    deploy(provider, server, RESOURCE_WAR_NAME_NEW,
        runtime_name=runtime_name, enabled=False, overwrite=True)
    check_deployment_disabled(provider, server, runtime_name)
    check_no_deployment_content(provider, server, runtime_name.replace(WAR_EXT, ''))
    deployment.enable()
    check_deployment_enabled(provider, server, runtime_name)
    check_deployment_content(provider, server, runtime_name.replace(WAR_EXT, ''),
                             RESOURCE_WAR_CONTENT_NEW)
