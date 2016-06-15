#!/usr/bin/python
# -*- coding: utf-8 -*-
import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.containers import list_tbl as list_tbl_pods
from cfme.containers import list_tbl as list_tbl_pods_rel
from cfme.containers import list_tbl as list_tbl_services
from cfme.containers import list_tbl as list_tbl_services_rel
from cfme.containers import list_tbl as list_tbl_nodes
from cfme.containers import list_tbl as list_tbl_nodes_rel
from cfme.containers import list_tbl as list_tbl_replicators
from cfme.containers import list_tbl as list_tbl_replicators_rel
from cfme.containers import list_tbl as list_tbl_images
from cfme.containers import list_tbl as list_tbl_images_rel
from cfme.containers import list_tbl as list_tbl_projects
from cfme.containers import list_tbl as list_tbl_projects_rel
from cfme.containers.pod import Pod
from cfme.containers.service import Service
from cfme.containers.node import Node
from cfme.containers.replicator import Replicator
from cfme.containers.image import Image
from cfme.containers.project import Project
from utils import testgen
from utils.version import current_version
from cfme.web_ui import InfoBlock

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.5"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")


# container pods
@pytest.mark.parametrize('rel',
                         ['Containers Provider',
                          'Project',
                          'Services',
                          'Replicator',
                          'Containers',
                          'Node'])
def test_pods_rel(provider, rel):
    sel.force_navigate('containers_pods')
    ui_pods = [r.name.text for r in list_tbl_pods.rows()]
    mgmt_objs = provider.mgmt.list_container_group()  # run only if table is not empty

    if ui_pods:
        # verify that mgmt pods exist in ui listed pods
        assert set(ui_pods).issubset(
            [obj.name for obj in mgmt_objs]), 'Missing objects'

    for name in ui_pods:
        obj = Pod(name, provider)

        val = obj.get_detail('Relationships', rel)
        if val == '0':
            continue
        obj.click_element('Relationships', rel)

        try:
            val = int(val)
            assert len([r for r in list_tbl_pods_rel.rows()]) == val
        except ValueError:
            assert val == InfoBlock.text('Properties', 'Name')


# container services
@pytest.mark.parametrize(
    'rel', ['Containers Provider', 'Project', 'Routes', 'Pods', 'Nodes'])
def test_services_rel(provider, rel):
    sel.force_navigate('containers_services')
    ui_services = [r.name.text for r in list_tbl_services.rows()]
    mgmt_objs = provider.mgmt.list_service()  # run only if table is not empty

    if ui_services:
        # verify that mgmt pods exist in ui listed pods
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
            assert len([r for r in list_tbl_services_rel.rows()]) == val
        except ValueError:
            assert val == InfoBlock.text('Properties', 'Name')


# container nodes
@pytest.mark.parametrize('rel',
                         ['Containers Provider',
                          'Routes',
                          'Services',
                          'Replicators',
                          'Pods',
                          'Containers'])
def test_nodes_rel(provider, rel):
    sel.force_navigate('containers_nodes')
    ui_nodes = [r.name.text for r in list_tbl_nodes.rows()]
    mgmt_objs = provider.mgmt.list_node()  # run only if table is not empty

    if ui_nodes:
        # verify that mgmt pods exist in ui listed pods
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
            assert len([r for r in list_tbl_nodes_rel.rows()]) == val
        except ValueError:
            assert val == InfoBlock.text('Properties', 'Name')


# container replicators
@pytest.mark.parametrize(
    'rel', ['Containers Provider', 'Project', 'Pods', 'Nodes'])
def test_replicators_rel(provider, rel):
    sel.force_navigate('containers_replicators')
    ui_replicators = [r.name.text for r in list_tbl_replicators.rows()]
    # run only if table is not empty
    mgmt_objs = provider.mgmt.list_replication_controller()

    if ui_replicators:
        # verify that mgmt pods exist in ui listed pods
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
            assert len([r for r in list_tbl_replicators_rel.rows()]) == val
        except ValueError:
            assert val == InfoBlock.text('Properties', 'Name')


# container images
@pytest.mark.parametrize('rel',
                         ['Containers Provider',
                          'Image Registry',
                          'Projects',
                          'Pods',
                          'Containers',
                          'Nodes'])
def test_images_rel(provider, rel):
    sel.force_navigate('containers_images')
    ui_images = [r.name.text for r in list_tbl_images.rows()]

    for name in ui_images:
        obj = Image(name, provider)

        val = obj.get_detail('Relationships', rel)
        if val == '0' or val == 'Unknown image source':
            continue
        obj.click_element('Relationships', rel)

        try:
            val = int(val)
            assert len([r for r in list_tbl_images_rel.rows()]) == val
        except ValueError:
            assert val == InfoBlock.text('Properties', 'Name')


# container projects
@pytest.mark.parametrize('rel',
                         ['Containers Provider',
                          'Routes',
                          'Services',
                          'Replicators',
                          'Pods',
                          'Nodes'])
def test_projects_rel(provider, rel):
    sel.force_navigate('containers_projects')
    ui_projects = [r.name.text for r in list_tbl_projects.rows()]
    mgmt_objs = provider.mgmt.list_project()  # run only if table is not empty

    if ui_projects:
        # verify that mgmt pods exist in ui listed pods
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
            assert len([r for r in list_tbl_projects_rel.rows()]) == val
        except ValueError:
            assert val == InfoBlock.text('Properties', 'Name')
