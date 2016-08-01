# -*- coding: utf-8 -*-
import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.containers.pod import Pod, list_tbl as list_tbl_pods
from cfme.containers.route import Route, list_tbl as list_tbl_routes
from cfme.containers.project import Project, list_tbl as list_tbl_projects
from cfme.containers.service import Service, list_tbl as list_tbl_services
from utils import testgen
from utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

# CMP-9911


@pytest.mark.parametrize('rel',
                         ['name',
                          'phase',
                          'creation_timestamp',
                          'resource_version',
                          'restart_policy',
                          'dns_policy',
                          'ip_address'
                          ])
def test_pods_properties_rel(provider, rel):
    """ This module verifies data integrity in the Properties table for:
        pods, routes and projects
    """
    sel.force_navigate('containers_pods')
    ui_pods = [r.name.text for r in list_tbl_pods.rows()]

    for name in ui_pods:
        obj = Pod(name, provider)
        assert getattr(obj.summary.properties, rel).text_value

# CMP-9877


@pytest.mark.parametrize('rel',
                         ['name',
                          'creation_timestamp',
                          'resource_version',
                          'host_name'
                          ])
def test_routes_properties_rel(provider, rel):
    sel.force_navigate('containers_routes')
    ui_routes = [r.name.text for r in list_tbl_routes.rows()]

    for name in ui_routes:
        obj = Route(name, provider)
        assert getattr(obj.summary.properties, rel).text_value

# CMP-9867


@pytest.mark.parametrize('rel',
                         ['name',
                          'creation_timestamp',
                          'resource_version'
                          ])
def test_projects_properties_rel(provider, rel):
    sel.force_navigate('containers_projects')
    ui_projects = [r.name.text for r in list_tbl_projects.rows()]

    for name in ui_projects:
        obj = Project(name, provider)
        assert getattr(obj.summary.properties, rel).text_value

# CMP-9884


@pytest.mark.parametrize('rel',
                         ['name',
                          'creation_timestamp',
                          'resource_version',
                          'session_affinity',
                          'type',
                          'portal_ip'
                          ])
def test_services_properties_rel(provider, rel):
    sel.force_navigate('containers_services')
    ui_services = [r.name.text for r in list_tbl_services.rows()]

    for name in ui_services:
        obj = Service(name, provider)
        assert getattr(obj.summary.properties, rel).text_value
