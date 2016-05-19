from random import sample

import pytest
from cfme.middleware.deployment import MiddlewareDeployment
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.usefixtures('single_middleware_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")


def test_list_deployments(provider):
    """Tests deployments list between UI, DB and Management system
    This test requires that no any other provider should exist before.

    Steps:
        * Get deployments list from UI
        * Get deployments list from Database
        * Get deployments list from Management system(Hawkular)
        * Compare size of all the list [UI, Database, Management system]
    """
    ui_deps = _get_deployments_set(MiddlewareDeployment.deployments())
    db_deps = _get_deployments_set(MiddlewareDeployment.deployments_in_db())
    mgmt_deps = _get_deployments_set(MiddlewareDeployment.deployments_in_mgmt(provider=provider))
    assert ui_deps == db_deps == mgmt_deps, \
        ("Lists of deployments mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_deps, db_deps, mgmt_deps))


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
        ("Lists of deployments mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_deps, db_deps, mgmt_deps))


def _get_deployments_set(deployments):
    """
    Return the set of deployments which contains only necessary fields,
    such as 'name' and 'server'
    """
    return set((deployment.name, deployment.server) for deployment in deployments)


def test_deployment(provider):
    """Tests deployment details on UI

    Steps:
        * Get deployments list from UI
        * Select up to 3 deployments randomly
        * Compare selected deployment details with CFME database
    """
    ui_deps = MiddlewareDeployment.deployments(provider=provider)
    assert len(ui_deps) > 0, "There is no deployment(s) available in UI"
    # select random deployments
    if len(ui_deps) > 3:
        sample_deps = sample(ui_deps, 3)
    else:
        sample_deps = ui_deps
    for dep_ui in sample_deps:
        # https://github.com/ManageIQ/manageiq/issues/8418, via server navigation failing
        dep_ui.server = None
        dep_db = dep_ui.deployment(method='db')
        assert dep_ui.name == dep_db.name, "deployment name does not match between UI and DB"
        dep_ui.validate_properties()
