# -*- coding: utf-8 -*-
import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.containers.pod import Pod
from cfme.containers.service import Service
from cfme.containers.node import Node
from cfme.containers.replicator import Replicator
from cfme.containers.image import Image
from cfme.containers.project import Project
from utils import testgen
from utils.version import current_version
from cfme.web_ui import InfoBlock, CheckboxTable

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.5"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

# CMP-9929 # CMP-9930 # CMP-9892 # CMP-9965 # CMP=9962 # CMP-9983
# CMP-9980 # CMP-9868 # CMP-9869


@pytest.mark.parametrize('rel',
                         ['Containers Provider',
                          'Project',
                          'Services',
                          'Replicator',
                          'Containers',
                          'Node'])
def test_pods_rel(provider, rel):
    """ This module verifies the integrity of the Relationships table
          We also verify that clicking on the Relationships table field
          takes the user to the correct page, and the number of rows
          that appears on that page is equal to the number in the
          Relationships table
    """

    sel.force_navigate('containers_pods')
    list_tbl_pod = CheckboxTable(table_locator="//div[@id='list_grid']//table")
    ui_pods = [r.name.text for r in list_tbl_pod.rows()]
    ui_pods_revised = filter(
        lambda ch: 'nginx' not in ch and not ch.startswith('metrics'),
        ui_pods)

    for name in ui_pods_revised:
        obj = Pod(name, provider)

        val = obj.get_detail('Relationships', rel)
        if val == '0':
            continue
        obj.click_element('Relationships', rel)

        try:
            val = int(val)
            assert len([r for r in list_tbl_pod.rows()]) == val
        except ValueError:
            assert val == InfoBlock.text('Properties', 'Name')


@pytest.mark.parametrize(
    'rel', ['Containers Provider', 'Project', 'Routes', 'Pods', 'Nodes'])
def test_services_rel(provider, rel):
    sel.force_navigate('containers_services')
    list_tbl_service = CheckboxTable(
        table_locator="//div[@id='list_grid']//table")
    ui_services = [r.name.text for r in list_tbl_service.rows()]
    mgmt_objs = provider.mgmt.list_service()

    if ui_services:
        assert set(ui_services).issubset(
            [obj.name for obj in mgmt_objs]), 'Missing objects'

    for name in ui_services:
        obj = Service(name, provider)

        val = obj.get_detail('Relationships', rel)
        if val == '0':
            continue
        obj.click_element('Relationships', rel)

        try:
            val = int(val)
            assert len([r for r in list_tbl_service.rows()]) == val
        except ValueError:
            assert val == InfoBlock.text('Properties', 'Name')


@pytest.mark.parametrize('rel',
                         ['Containers Provider',
                          'Routes',
                          'Services',
                          'Replicators',
                          'Pods',
                          'Containers'])
def test_nodes_rel(provider, rel):
    sel.force_navigate('containers_nodes')
    list_tbl_node = CheckboxTable(
        table_locator="//div[@id='list_grid']//table")
    ui_nodes = [r.name.text for r in list_tbl_node.rows()]
    mgmt_objs = provider.mgmt.list_node()

    if ui_nodes:
        assert set(ui_nodes).issubset(
            [obj.name for obj in mgmt_objs]), 'Missing objects'

    for name in ui_nodes:
        obj = Node(name, provider)

        val = obj.get_detail('Relationships', rel)
        if val == '0':
            continue
        obj.click_element('Relationships', rel)

        try:
            val = int(val)
            assert len([r for r in list_tbl_node.rows()]) == val
        except ValueError:
            assert val == InfoBlock.text('Properties', 'Name')


@pytest.mark.parametrize(
    'rel', ['Containers Provider', 'Project', 'Pods', 'Nodes'])
def test_replicators_rel(provider, rel):
    sel.force_navigate('containers_replicators')
    list_tbl_replicator = CheckboxTable(
        table_locator="//div[@id='list_grid']//table")
    ui_replicators = [r.name.text for r in list_tbl_replicator.rows()]
    mgmt_objs = provider.mgmt.list_replication_controller()

    if ui_replicators:
        assert set(ui_replicators).issubset(
            [obj.name for obj in mgmt_objs]), 'Missing objects'

    for name in ui_replicators:
        obj = Replicator(name, provider)

        val = obj.get_detail('Relationships', rel)
        if val == '0':
            continue
        obj.click_element('Relationships', rel)

        try:
            val = int(val)
            assert len([r for r in list_tbl_replicator.rows()]) == val
        except ValueError:
            assert val == InfoBlock.text('Properties', 'Name')


@pytest.mark.parametrize('rel',
                         ['Containers Provider',
                          'Image registry',
                          'Projects',
                          'Pods',
                          'Containers',
                          'Nodes'])
def test_images_rel(provider, rel):
    sel.force_navigate('containers_images')
    list_tbl_image = CheckboxTable(
        table_locator="//div[@id='list_grid']//table")
    ui_images = [r.name.text for r in list_tbl_image.rows()]

    for name in ui_images:
        obj = Image(name, provider)

        val = obj.get_detail('Relationships', rel)
        assert val != 'Unknown image source'
        obj.click_element('Relationships', rel)

        try:
            val = int(val)
            assert len([r for r in list_tbl_image.rows()]) == val
        except ValueError:
            assert val == InfoBlock.text('Properties', 'Name')


@pytest.mark.parametrize('rel',
                         ['Containers Provider',
                          'Routes',
                          'Services',
                          'Replicators',
                          'Pods',
                          'Nodes'])
def test_projects_rel(provider, rel):
    sel.force_navigate('containers_projects')
    list_tbl_project = CheckboxTable(
        table_locator="//div[@id='list_grid']//table")
    ui_projects = [r.name.text for r in list_tbl_project.rows()]
    mgmt_objs = provider.mgmt.list_project()

    if ui_projects:
        assert set(ui_projects).issubset(
            [obj.name for obj in mgmt_objs]), 'Missing objects'

    for name in ui_projects:
        obj = Project(name, provider)

        val = obj.get_detail('Relationships', rel)
        if val == '0':
            continue
        obj.click_element('Relationships', rel)

        try:
            val = int(val)
            assert len([r for r in list_tbl_project.rows()]) == val
        except ValueError:
            assert val == InfoBlock.text('Properties', 'Name')
