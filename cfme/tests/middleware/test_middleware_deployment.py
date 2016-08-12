from __future__ import unicode_literals
import pytest

import os
import fauxfactory
from cfme.middleware import get_random_list
from cfme.middleware.deployment import MiddlewareDeployment
from cfme.middleware.server import MiddlewareServer
from utils import testgen
from utils.version import current_version
from utils.wait import wait_for
from utils.path import middleware_resources_path


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")
ITEMS_LIMIT = 5  # when we have big list, limit number of items to test

RESOURCE_WAR_NAME = 'cfme_test_war_middleware.war'
RESOURCE_JAR_NAME = 'cfme_test_jar_middleware.jar'
RESOURCE_EAR_NAME = 'cfme_test_ear_middleware.ear'

EAP_PRODUCT_NAME = 'JBoss EAP'
HAWKULAR_PRODUCT_NAME = 'Hawkular'


def test_list_deployments(provider):
    """Tests deployments list between UI, DB and management system

    Steps:
        * Get deployments list from UI for whole Middleware
        * Get deployments list from Database for Hawkular Local server
        * Get deployments list from Management system for Hawkular Local server
        * Verifies that UI list contains all DB entities
        * Verifies that UI list contains all MGMT entities
    """
    server = get_server(provider, HAWKULAR_PRODUCT_NAME)
    ui_deps = get_deployments_set(MiddlewareDeployment.deployments())
    db_deps = get_deployments_set(MiddlewareDeployment.deployments_in_db(
        provider=provider, server=server))
    mgmt_deps = get_deployments_set(MiddlewareDeployment.deployments_in_mgmt(
        provider=provider, server=server))
    assert ui_deps >= db_deps, \
        ("Lists of deployments in UI does not contain the list in DB! UI:{}, DB:{}"
         .format(ui_deps, db_deps))
    assert ui_deps >= mgmt_deps, \
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
    server = get_server(provider, HAWKULAR_PRODUCT_NAME)
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
        * Get deployments list from Database for Hawkular Local server
        * Get deployments list from Management system(Hawkular) for Hawkular Local server
        * Verifies that UI list contains all DB entities
        * Verifies that UI list contains all MGMT entities
    """
    server = get_server(provider, HAWKULAR_PRODUCT_NAME)
    ui_deps = get_deployments_set(MiddlewareDeployment.deployments(provider=provider))
    db_deps = get_deployments_set(MiddlewareDeployment.deployments_in_db(
        provider=provider, server=server))
    mgmt_deps = get_deployments_set(MiddlewareDeployment.deployments_in_mgmt(
        provider=provider, server=server))
    assert ui_deps >= db_deps, \
        ("Lists of deployments in UI does not contain the list in DB! UI:{}, DB:{}"
         .format(ui_deps, db_deps))
    assert ui_deps >= mgmt_deps, \
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
    server = get_server(provider, HAWKULAR_PRODUCT_NAME)
    ui_deps = get_deployments_set(
        MiddlewareDeployment.deployments(provider=provider, server=server))
    db_deps = get_deployments_set(
        MiddlewareDeployment.deployments_in_db(provider=provider, server=server))
    mgmt_deps = get_deployments_set(
        MiddlewareDeployment.deployments_in_mgmt(provider=provider, server=server))
    assert ui_deps == db_deps == mgmt_deps, \
        ("Lists of deployments mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_deps, db_deps, mgmt_deps))


def test_deployment(provider):
    """Tests deployment details on UI

    Steps:
        * Get deployments list from UI
        * Select up to `ITEMS_LIMIT` deployments randomly
        * Compare selected deployment details with CFME database
    """
    ui_deps = MiddlewareDeployment.deployments(provider=provider,
                                               server=get_server(provider, HAWKULAR_PRODUCT_NAME))
    assert len(ui_deps) > 0, "There is no deployment(s) available in UI"
    for dep_ui in get_random_list(ui_deps, ITEMS_LIMIT):
        dep_db = dep_ui.deployment(method='db')
        assert dep_ui.name == dep_db.name, "deployment name does not match between UI and DB"
        assert dep_ui.server.name == dep_db.server.name, \
            "deployment server name does not match between UI and DB"
        dep_ui.validate_properties()


@pytest.mark.parametrize("archive_name", [RESOURCE_WAR_NAME, RESOURCE_JAR_NAME, RESOURCE_EAR_NAME])
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
    server = get_server(provider, EAP_PRODUCT_NAME)
    deploy(provider, server, get_resource_path(archive_name))
    # disable for now as not stable test because of performance issue #10138
    # _check_deployment_enabled(provider, server, runtime_name)
    # deployment = _get_deployment_from_list(provider, server, runtime_name)
    # deployment.validate_properties()


@pytest.mark.meta(blockers=['GH#ManageIQ/manageiq:10138'])
@pytest.mark.parametrize("archive_name", [RESOURCE_WAR_NAME, RESOURCE_JAR_NAME, RESOURCE_EAR_NAME])
def test_undeploy(provider, archive_name):
    """Tests Undeployment of archive from EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Deplays some deployment archive into server.
        * Select that deployment from deployments list.
        * Performs "Undeploy" toolbar operation on it.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently undeployed archive's status is Disabled.
        * Selects that archive from the list to load details.
        * Verifies that properties of deplyment's summary page and the status is Disabled.
    """
    server = get_server(provider, EAP_PRODUCT_NAME)
    runtime_name = deploy(provider, server, get_resource_path(archive_name))
    check_deployment_enabled(provider, server, runtime_name)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.undeploy()
    check_deployment_disabled(provider, server, runtime_name)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.validate_properties()


@pytest.mark.meta(blockers=['GH#ManageIQ/manageiq:10138'])
@pytest.mark.parametrize("archive_name", [RESOURCE_WAR_NAME, RESOURCE_JAR_NAME, RESOURCE_EAR_NAME])
def test_redeploy(provider, archive_name):
    """Tests Redeployment of undeployed archive into EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Deploys some deployment archive into server.
        * Undeploys that archive.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently redeployed archive's status is Enabled.
        * Selects that archive from the list to load details.
        * Verifies that properties of deplyment's summary page and the status is Enabled.
    """
    server = get_server(provider, EAP_PRODUCT_NAME)
    runtime_name = deploy(provider, server, get_resource_path(archive_name))
    check_deployment_enabled(provider, server, runtime_name)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.undeploy()
    check_deployment_disabled(provider, server, runtime_name)
    deployment.redeploy()
    # enable when #9876 is fixed
    # _check_deployment_enabled(provider, server, runtime_name)
    # deployment = _get_deployment_from_list(provider, server, runtime_name)
    # deployment.validate_properties()


@pytest.mark.meta(blockers=['GH#ManageIQ/manageiq:10138'])
@pytest.mark.parametrize("archive_name", [RESOURCE_WAR_NAME, RESOURCE_JAR_NAME, RESOURCE_EAR_NAME])
def test_stop(provider, archive_name):
    """Tests Stopping of archive from EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Deploys some deployment archive into server.
        * Select that deployment from deployments list.
        * Performs "Stop" toolbar operation on it.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently stopped archive's status is Disabled.
        * Selects that archive from the list to load details.
        * Verifies that properties of deplyment's summary page and the status is Disabled.
    """
    server = get_server(provider, EAP_PRODUCT_NAME)
    runtime_name = deploy(provider, server, get_resource_path(archive_name))
    check_deployment_enabled(provider, server, runtime_name)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.stop()
    check_deployment_disabled(provider, server, runtime_name)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.validate_properties()


@pytest.mark.meta(blockers=['GH#ManageIQ/manageiq:10138'])
@pytest.mark.parametrize("archive_name", [RESOURCE_WAR_NAME, RESOURCE_JAR_NAME, RESOURCE_EAR_NAME])
def test_start(provider, archive_name):
    """Tests Starting of stopped archive into EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Deploys some deployment archive into server.
        * Stops that archive.
        * Refreshes the provider.
        * Lists all deployments on EAP server.
        * Verified the recently stopped archive's status is Enabled.
        * Selects that archive from the list to load details.
        * Verifies that properties of deplyment's summary page and the status is Enabled.
    """
    server = get_server(provider, EAP_PRODUCT_NAME)
    runtime_name = deploy(provider, server, get_resource_path(archive_name))
    check_deployment_enabled(provider, server, runtime_name)
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.stop()
    check_deployment_disabled(provider, server, runtime_name)
    deployment.start()
    # enable when #10111 is fixed
    # _check_deployment_enabled(provider, server, runtime_name)
    # deployment = _get_deployment_from_list(provider, server, runtime_name)
    # deployment.validate_properties()


def get_deployments_set(deployments):
    """
    Return the set of deployments which contains only necessary fields,
    such as 'name' and 'server'
    """
    return set((deployment.name, deployment.server.name) for deployment in deployments)


def get_deployments_statuses(deployments):
    """
    Return the map of deployments which contains,
    'name' as key, 'status' as value
    """
    return {deployment.name: deployment.status for deployment in deployments}


def deploy(provider, server, file_path):
    runtime_name = "{}_{}".format(fauxfactory.gen_alpha(8).lower(), os.path.basename(file_path))
    server.add_deployment(file_path, runtime_name)
    provider.refresh_provider_relationships(method='ui')
    return runtime_name


def get_server(provider, product):
    for server in MiddlewareServer.servers(provider=provider):
        if server.product == product:
            return server
    else:
        raise ValueError('{} server was not found in servers list'.format(provider))


def get_resource_path(archive_name):
    return middleware_resources_path.join(archive_name).strpath


def get_deployment_from_list(provider, server, runtime_name):
    for deployment in MiddlewareDeployment.deployments(provider=provider, server=server):
        if deployment.name == runtime_name:
            return deployment
    raise ValueError('Recently deployed archive {} was not found in deployments list'
                     .format(runtime_name))


def check_deployment_appears(provider, server, runtime_name):
    provider.refresh_provider_relationships(method='ui')
    wait_for(lambda: runtime_name in
             get_deployments_statuses(MiddlewareDeployment.deployments(provider=provider,
                                                                   server=server)),
            delay=30, num_sec=1200,
            message='Deployment {} must be found for server {}'
            .format(runtime_name, server.name))


def check_deployment_enabled(provider, server, runtime_name):
    check_deployment_appears(provider, server, runtime_name)
    wait_for(lambda:
             get_deployments_statuses(MiddlewareDeployment.deployments(provider=provider,
                                            server=server))[runtime_name] == 'Enabled',
            delay=120, num_sec=1800,
            message='Deployment {} must be Enabled for server {}'
            .format(runtime_name, server.name))


def check_deployment_disabled(provider, server, runtime_name):
    provider.refresh_provider_relationships(method='ui')
    wait_for(lambda:
             get_deployments_statuses(MiddlewareDeployment.deployments(provider=provider,
                                            server=server))[runtime_name] == 'Disabled',
            delay=120, num_sec=1800,
            message='Deployment {} must be Disabled for server {}'
            .format(runtime_name, server.name))
