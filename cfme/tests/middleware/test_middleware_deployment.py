from random import sample

import pytest
from cfme.middleware.deployment import MiddlewareDeployment
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")


def test_list_deployments(provider):
    """Tests deployments count between UI, DB and Management system

    Steps:
        * Get deployments list from UI
        * Get deployments list from Database
        * Get deployments list from Management system(Hawkular)
        * Compare size of all the list [UI, Database, Management system]
    """
    ui_deps = MiddlewareDeployment.deployments(provider=provider)
    db_deps = MiddlewareDeployment.deployments_in_db()
    mgmt_deps = MiddlewareDeployment.deployments_in_mgmt(provider)
    assert len(ui_deps) == len(db_deps) == len(mgmt_deps), \
        ("Size of deployments mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(len(ui_deps), len(db_deps), len(mgmt_deps)))


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
