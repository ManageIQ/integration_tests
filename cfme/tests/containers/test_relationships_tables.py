# -*- coding: utf-8 -*-
import pytest

from cfme.containers.pod import Pod
from cfme.containers.service import Service
from cfme.containers.node import Node
from cfme.containers.replicator import Replicator
from cfme.containers.image import Image
from cfme.containers.project import Project
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import InfoBlock, CheckboxTable, paginator, toolbar as tb
from utils import testgen, version
from utils.appliance.implementations.ui import navigate_to
from utils.log import logger
from utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")


# 9929 #9930


@pytest.mark.parametrize('rel',
                         ['Containers Provider',
                          'Project',
                          'Container Services',
                          'Replicator',
                          'Containers',
                          'Container Images',
                          'Node'])
def test_pods_rel(provider, rel):
    """   This module verifies the fields in the Relationships table
          We also verify that clicking on the Relationships table field
          takes the user to the correct page, and the number of rows
          that appears on that page is equal to the number in the
          Relationships table
    """
    navigate_to(Pod, 'All')
    tb.select('List View')
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


# 9892


@pytest.mark.parametrize(
    'rel', ['Containers Provider', 'Project', 'Routes', 'Pods', 'Nodes'])
def test_services_rel(provider, rel):
    navigate_to(Service, 'All')
    tb.select('List View')
    list_tbl_service = CheckboxTable(
        table_locator="//div[@id='list_grid']//table")
    ui_services = [r.name.text for r in list_tbl_service.rows()]
    mgmt_objs = provider.mgmt.list_service()

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

# 9965 #9962


@pytest.mark.parametrize('rel', [
    'Containers Provider',
    'Routes',
    'Container Services',
    'Replicators',
    'Pods',
    'Container Images',
    'Containers'
])
def test_nodes_rel(provider, rel):
    navigate_to(provider, 'Details')

    sel.click(InfoBlock.element('Relationships', 'Nodes'))

    list_tbl_node = CheckboxTable(
        table_locator="//div[@id='list_grid']//table")
    ui_nodes = [r.name.text for r in list_tbl_node.rows()]
    mgmt_objs = provider.mgmt.list_node()

    assert set(ui_nodes).issubset(
        [obj.name for obj in mgmt_objs]), 'Missing objects'

    for name in ui_nodes:
        node = Node(name, provider)

        val = node.get_detail('Relationships', rel)
        if val == '0':
            # the row can't be clicked when there are no items, and has class
            # 'no-hover'
            logger.info('No items for node relationship: {}'.format(rel))
            continue
        # Should already be here, but just in case
        navigate_to(node, 'Details')
        sel.click(InfoBlock.element('Relationships', rel))

        try:
            val = int(val)
            # best effort to include all items from rel in one page
            if paginator.page_controls_exist():
                logger.info(
                    'Setting results per page to 1000 for {}'.format(rel))
                paginator.results_per_page(1000)
            else:
                logger.warning('Unable to increase results per page, '
                               'assertion against number of rows may fail.')
            assert len([r for r in list_tbl_node.rows()]) == val
        except ValueError:  # if the conversion to integer failed, its a non-scalar relationship
            assert val == InfoBlock.text('Properties', 'Name')


@pytest.mark.parametrize(
    'rel', ['Containers Provider', 'Project', 'Pods', 'Nodes'])
def test_replicators_rel(provider, rel):
    navigate_to(Replicator, 'All')
    tb.select('List View')
    list_tbl_replicator = CheckboxTable(
        table_locator="//div[@id='list_grid']//table")
    ui_replicators = [r.name.text for r in list_tbl_replicator.rows()]
    mgmt_objs = provider.mgmt.list_replication_controller()

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

# 9983 #9980


@pytest.mark.meta(blockers=[1365878])
@pytest.mark.parametrize('rel, detailfield', [
    ('Containers Provider', 'Name'),
    ('Image Registry', 'Host'),
    ('Projects', None),
    ('Pods', None),
    ('Containers', None),
    ('Nodes', None)
])
def test_images_rel(provider, rel, detailfield):
    """ https://bugzilla.redhat.com/show_bug.cgi?id=1365878
    """
    # Nav to provider first
    navigate_to(provider, 'Details')

    # Then to container images for that provider
    # Locate Relationships table in provider details
    images_key = ({
        version.LOWEST: 'Images',
        '5.7': 'Container Images'
    })
    sel.click(InfoBlock.element('Relationships', version.pick(images_key)))

    # Get the names of all the container images from the table
    list_tbl_image = CheckboxTable(
        table_locator="//div[@id='list_grid']//table")
    ui_images = [r.name.text for r in list_tbl_image.rows()]

    for name in ui_images:
        img = Image(name, provider)
        navigate_to(img, 'Details')

        val = img.get_detail('Relationships', rel)
        assert val != 'Unknown image source'

        sel.click(InfoBlock.element('Relationships', rel))

        # Containers Provider and Image Registry are string values
        # Other rows in the table show the number of the given items
        if rel in ['Containers Provider', 'Image Registry']:
            assert val == InfoBlock.text('Properties', detailfield)
        else:
            val = int(val)
            # There might be more than 1 page of items
            if paginator.page_controls_exist():
                paginator.results_per_page(1000)
            assert len([r for r in list_tbl_image.rows()]) == val


# 9868 #9869


@pytest.mark.parametrize('rel',
                         ['Containers Provider',
                          'Routes',
                          'Container Services',
                          'Replicators',
                          'Pods',
                          'Container Images',
                          'Nodes'])
def test_projects_rel(provider, rel):
    sel.force_navigate('containers_projects')
    tb.select('List View')
    list_tbl_project = CheckboxTable(
        table_locator="//div[@id='list_grid']//table")
    ui_projects = [r.name.text for r in list_tbl_project.rows()]
    mgmt_objs = provider.mgmt.list_project()

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
