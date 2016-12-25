import pytest

from cfme.containers.pod import Pod, list_tbl as list_tbl_pods
from cfme.containers.route import Route, list_tbl as list_tbl_routes
from cfme.containers.project import Project, list_tbl as list_tbl_projects
from cfme.containers.service import Service, list_tbl as list_tbl_services
from utils import testgen
from utils.version import current_version
from utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")


# CMP-9911


def test_pods_properties(provider):
    """ Steps:
    Containers -- > Containers -- > Pods
    Call the relevant API and verify data integrity for the following fields:
    name, project_name, restart_policy, dns_policy

    """

    navigate_to(Pod, 'All')
    ui_pods = [r.name.text for r in list_tbl_pods.rows()]

    mgmt_objs_pods = provider.mgmt.list_container_group()

    if ui_pods:
        assert set(ui_pods).issubset([obj.name for obj in mgmt_objs_pods]), \
            'Missing objects if compared to mgmt provider'


# CMP-9877


def test_routes_properties(provider):
    """ Steps:
    Containers -- > Containers -- > Routes
    Call the relevant API and verify data integrity for the following fields:
    name, project_name, restart_policy, dns_policy

    """
    navigate_to(Route, 'All')
    ui_routes = [r.name.text for r in list_tbl_routes.rows()]

    mgmt_objs_routes = provider.mgmt.list_route()

    if ui_routes:
        assert set(ui_routes).issubset([obj.name for obj in mgmt_objs_routes]), \
            'Missing objects if compared to mgmt provider'


# CMP-9867


def test_projects_properties(provider):
    """ Steps:
    Containers -- > Containers -- > Projects
    Call the relevant API and verify data integrity for the following fields:
    name, project_name, restart_policy, dns_policy

    """
    navigate_to(Project, 'All')
    ui_projects = [r.name.text for r in list_tbl_projects.rows()]

    mgmt_objs_projects = provider.mgmt.list_project()

    if ui_projects:
        assert set(ui_projects).issubset([obj.name for obj in mgmt_objs_projects]), \
            'Missing objects if compared to mgmt provider'


# CMP-9884


def test_services_properties(provider):
    """ Steps:
    Containers -- > Containers -- > Container Services
    Call the relevant API and verify data integrity for the following fields:
    name, project_name, restart_policy, dns_policy

    """
    navigate_to(Service, 'All')
    ui_services = [r.name.text for r in list_tbl_services.rows()]

    mgmt_objs_services = provider.mgmt.list_service()

    if ui_services:
        assert set(ui_services).issubset([obj.name for obj in mgmt_objs_services]), \
            'Missing objects if compared to mgmt provider'
