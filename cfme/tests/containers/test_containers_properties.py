# -*- coding: utf-8 -*-
import pytest

from cfme.containers.pod import Pod, list_tbl as list_tbl_pods
from cfme.containers.provider import ContainersProvider
from cfme.containers.route import Route, list_tbl as list_tbl_routes
from cfme.containers.project import Project, list_tbl as list_tbl_projects
from cfme.containers.service import Service, list_tbl as list_tbl_services

from utils import testgen
from utils.version import current_version
from utils.appliance.implementations.ui import navigate_to
import random


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


def randomized_names_of(tbl, count):
    names = [r.name.text for r in tbl.rows()]
    random.shuffle(names)  # inplace
    return names[:min(count, tbl.row_count())]


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
    """ Properties table fields tests - Containers Pods' summary page
    This test verifies the fields of the Properties table in Containers Pods'
    details menu
    Steps:
    Containers -- > Containers Pods
    Loop through each Pod object in the table and check validity of
    the fields in the Properties table
    """
    navigate_to(Pod, 'All')
    ui_pods = randomized_names_of(list_tbl_pods, 2)

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
    """ Properties table fields tests - Containers Routes' summary page
    This test verifies the fields of the Properties table in Containers Routes'
    details menu
    Steps:
    Containers -- > Containers Routes
    Loop through each Route object in the table and check validity of
    the fields in the Properties table
    """
    navigate_to(Route, 'All')
    ui_routes = randomized_names_of(list_tbl_routes, 2)

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
    """ Properties table fields tests - Containers Projects' summary page
    This test verifies the fields of the Properties table in Containers Projects'
    details menu
    Steps:
    Containers -- > Containers Projects
    Loop through each Project object in the table and check validity of
    the fields in the Properties table
    """
    navigate_to(Project, 'All')
    ui_projects = randomized_names_of(list_tbl_projects, 2)

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
    """ Properties table fields tests - Containers Services' summary page
    This test verifies the fields of the Properties table in Containers Services'
    details menu
    Steps:
    Containers -- > Containers Services
    Loop through each Service object in the table and check validity of
    the fields in the Properties table
    """
    navigate_to(Service, 'All')
    ui_services = randomized_names_of(list_tbl_services, 2)

    for name in ui_services:
        obj = Service(name, provider)
        assert getattr(obj.summary.properties, rel).text_value
