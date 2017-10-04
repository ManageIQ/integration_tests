"""
This test can run only after overcloud cloud provider created and linked to
undercloud infra provider, need to compare the cloud providers with the
results of the relationships
"""
import pytest

import cfme.fixtures.pytest_selenium as sel
from cfme.infrastructure.provider.openstack_infra import OpenstackInfraProvider
from cfme.web_ui import InfoBlock, Table
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [pytest.mark.meta(server_roles='+smartproxy +smartstate'),
              pytest.mark.usefixtures("setup_provider_modscope")]


pytest_generate_tests = testgen.generate([OpenstackInfraProvider], scope='module')


def test_assigned_roles(provider):
    navigate_to(provider, 'Details')
    try:
        res = provider.get_detail('Relationships', 'Deployment Roles')
    except NameError:
        res = provider.get_detail('Relationships', 'Clusters / Deployment Roles')
    assert int(res) > 0


def test_nodes(provider):
    navigate_to(provider, 'Details')
    nodes = len(provider.mgmt.list_node())

    assert int(provider.get_detail('Relationships', 'Nodes')) == nodes


def test_templates(provider, soft_assert):
    navigate_to(provider, 'Details')
    images = [i.name for i in provider.mgmt.images]

    assert int(provider.get_detail('Relationships', 'Templates')) == len(images)
    sel.click(InfoBlock.element('Relationships', 'Templates'))
    table = Table("//table[contains(@class, 'table')]")

    for image in images:
        cell = table.find_cell('Name', image)
        soft_assert(cell, 'Missing template: {}'.format(image))


def test_stacks(provider):
    navigate_to(provider, 'Details')
    """
    todo get the list of tenants from external resource and compare
    it with result - currently not 0
    """

    assert int(provider.get_detail('Relationships', 'Orchestration stacks')) > 0
