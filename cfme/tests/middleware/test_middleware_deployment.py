import pytest
from cfme.middleware import get_random_list
from cfme.middleware.deployment import MiddlewareDeployment
from cfme.middleware.server import MiddlewareServer
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")
ITEMS_LIMIT = 5  # when we have big list, limit number of items to test


def test_list_deployments():
    """Tests deployments list between UI, DB and management system

    Steps:
        * Get deployments list from UI
        * Get deployments list from Database
        * Compare size of all the list [UI, Database, Management system]
    """
    ui_deps = _get_deployments_set(MiddlewareDeployment.deployments())
    db_deps = _get_deployments_set(MiddlewareDeployment.deployments_in_db())
    mgmt_deps = _get_deployments_set(MiddlewareDeployment.deployments_in_mgmt())
    assert ui_deps == db_deps == mgmt_deps, \
        ("Lists of deployments mismatch! UI:{}, DB:{}, MGMT:{}".format(ui_deps, db_deps, mgmt_deps))


def test_list_server_deployments():
    """Gets servers list and tests deployments list for each server

    Steps:
        * Get servers list from UI
        * Get deployments list from UI of server
        * Get deployments list from Database of server
        * Compare size of all the list [UI, Database]
    """
    servers = MiddlewareServer.servers()
    assert len(servers) > 0, "There is no server(s) available in UI"
    for server in get_random_list(servers, ITEMS_LIMIT):
        ui_deps = _get_deployments_set(MiddlewareDeployment.deployments(server=server))
        db_deps = _get_deployments_set(MiddlewareDeployment.deployments_in_db(server=server))
        assert ui_deps == db_deps, \
            ("Lists of deployments mismatch! UI:{}, DB:{}".format(ui_deps, db_deps))


def test_list_provider_deployments(provider):
    """Tests deployments list from current Provider between UI, DB and Management system

    Steps:
        * Get deployments list from UI of provider
        * Get deployments list from Database of provider
        * Get deployments list from Management system(Hawkular)
        * Compare size of all the list [UI, Database, Management system]
    """
    ui_deps = _get_deployments_set(MiddlewareDeployment.deployments(provider=provider))
    db_deps = _get_deployments_set(MiddlewareDeployment.deployments_in_db(provider=provider))
    mgmt_deps = _get_deployments_set(MiddlewareDeployment.deployments_in_mgmt(provider=provider))
    assert ui_deps == db_deps == mgmt_deps, \
        ("Lists of deployments mismatch! UI:{}, DB:{}, MGMT:{}".format(ui_deps, db_deps, mgmt_deps))


def test_list_provider_server_deployments(provider):
    """Tests deployments list from current Provider for each server
    between UI, DB and Management system

    Steps:
        * Get servers list from UI of provider
        * Get deployments list for the server
        * Get deployments list from UI of provider, server
        * Get deployments list from Database of provider, server
        * Get deployments list from Database of provider, server
        * Get deployments list from Management system(Hawkular) of server
        * Compare size of all the list [UI, Database, Management system]
    """
    servers = MiddlewareServer.servers(provider=provider)
    assert len(servers) > 0, "There is no server(s) available in UI"
    for server in get_random_list(servers, ITEMS_LIMIT):
        ui_deps = _get_deployments_set(
            MiddlewareDeployment.deployments(provider=provider, server=server))
        db_deps = _get_deployments_set(
            MiddlewareDeployment.deployments_in_db(provider=provider, server=server))
        mgmt_deps = _get_deployments_set(
            MiddlewareDeployment.deployments_in_mgmt(provider=provider, server=server))
        assert ui_deps == db_deps == mgmt_deps, \
            ("Lists of deployments mismatch! UI:{}, DB:{}, MGMT:{}"
             .format(ui_deps, db_deps, mgmt_deps))


def _get_deployments_set(deployments):
    """
    Return the set of deployments which contains only necessary fields,
    such as 'name' and 'server'
    """
    return set((deployment.name, deployment.server.name) for deployment in deployments)


def test_deployment(provider):
    """Tests deployment details on UI

    Steps:
        * Get deployments list from UI
        * Select up to `ITEMS_LIMIT` deployments randomly
        * Compare selected deployment details with CFME database
    """
    ui_deps = MiddlewareDeployment.deployments(provider=provider)
    assert len(ui_deps) > 0, "There is no deployment(s) available in UI"
    for dep_ui in get_random_list(ui_deps, ITEMS_LIMIT):
        dep_db = dep_ui.deployment(method='db')
        assert dep_ui.name == dep_db.name, "deployment name does not match between UI and DB"
        assert dep_ui.server.name == dep_db.server.name, \
            "deployment server name does not match between UI and DB"
        dep_ui.validate_properties()
