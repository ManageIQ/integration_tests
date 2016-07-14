#!/usr/bin/python
# -*- coding: utf-8 -*-
# the test performs field verification in Properties table
# Polarion test 9911
# Polarion test 9877
# Polarion test 9867
import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.containers.pod import Pod
from cfme.containers.route import Route
from cfme.containers.project import Project
from utils import testgen
from utils.version import current_version
from cfme.web_ui import CheckboxTable

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")


# container pods Properties table data validation
@pytest.mark.parametrize('rel',
                         ['Name',
                          'Phase',
                          'Creation timestamp',
                          'Resource version',
                          'Restart policy',
                          'DNS Policy',
                          'IP Address'])
def test_pods_properties_rel(provider, rel):
    sel.force_navigate('containers_pods')
    list_tbl_pod = CheckboxTable(table_locator="//div[@id='list_grid']//table")
    ui_pods = [r.name.text for r in list_tbl_pod.rows()]
    mgmt_objs = provider.mgmt.list_container_group()  # run only if table is not empty

    if ui_pods:
        # verify that mgmt pods exist in ui listed pods
        assert set(ui_pods).issubset(
            [obj.name for obj in mgmt_objs]), 'Missing objects'

    for name in ui_pods:
        obj = Pod(name, provider)

        val = str(obj.get_detail('Properties', rel))
        if val:
            print ('\n' + val)
        else:
            print "Data integrity validation failed"


# container routes Properties table validation
@pytest.mark.parametrize('rel',
                         ['Name',
                          'Creation timestamp',
                          'Resource version',
                          'Host Name'])
def test_routes_properties_rel(provider, rel):
    sel.force_navigate('containers_routes')
    list_tbl_route = CheckboxTable(
        table_locator="//div[@id='list_grid']//table")
    ui_routes = [r.name.text for r in list_tbl_route.rows()]
    mgmt_objs = provider.mgmt.list_route()  # run only if table is not empty

    if ui_routes:
        # verify that mgmt routes exist in ui listed routes
        assert set(ui_routes).issubset(
            [obj.name for obj in mgmt_objs]), 'Missing objects'

    for name in ui_routes:
        obj = Route(name, provider)

        val = str(obj.get_detail('Properties', rel))
        if val:
            print ('\n' + val)
        else:
            print "Data integrity validation failed"


# container projects Properties table validation
@pytest.mark.parametrize('rel',
                         ['Name',
                          'Creation timestamp',
                          'Resource version'])
def test_projects_properties_rel(provider, rel):
    sel.force_navigate('containers_projects')
    list_tbl_project = CheckboxTable(
        table_locator="//div[@id='list_grid']//table")
    ui_projects = [r.name.text for r in list_tbl_project.rows()]
    mgmt_objs = provider.mgmt.list_project()  # run only if table is not empty

    if ui_projects:
        # verify that mgmt projects exist in ui listed projects
        assert set(ui_projects).issubset(
            [obj.name for obj in mgmt_objs]), 'Missing objects'

    for name in ui_projects:
        obj = Project(name, provider)

        val = str(obj.get_detail('Properties', rel))
        if val:
            print ('\n' + val)
        else:
            print "Data integrity validation failed"
