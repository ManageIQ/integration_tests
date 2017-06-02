from random import shuffle

import pytest

from utils import testgen
from utils.version import current_version
from cfme.web_ui import paginator, summary_title

from cfme.containers.pod import Pod
from cfme.containers.provider import ContainersProvider, navigate_and_get_rows,\
    ContainersTestItem
from cfme.containers.service import Service
from cfme.containers.node import Node
from cfme.containers.replicator import Replicator
from cfme.containers.image import Image
from cfme.containers.project import Project
from cfme.containers.template import Template
from cfme.containers.container import Container
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.volume import Volume


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


# The polarion markers below are used to mark the test item
# with polarion test case ID.
# TODO: future enhancement - https://github.com/pytest-dev/pytest/pull/1921


TEST_ITEMS = [
    pytest.mark.polarion('CMP-9851')(ContainersTestItem(ContainersProvider, 'CMP-9851')),
    pytest.mark.polarion('CMP-9947')(ContainersTestItem(Container, 'CMP-9947')),
    pytest.mark.polarion('CMP-9929')(ContainersTestItem(Pod, 'CMP-9929')),
    pytest.mark.polarion('CMP-10564')(ContainersTestItem(Service, 'CMP-10564')),
    pytest.mark.polarion('CMP-9962')(ContainersTestItem(Node, 'CMP-9962')),
    pytest.mark.polarion('CMP-10565')(ContainersTestItem(Replicator, 'CMP-10565')),
    pytest.mark.polarion('CMP-9980')(ContainersTestItem(Image, 'CMP-9980')),
    pytest.mark.polarion('CMP-9994')(ContainersTestItem(ImageRegistry, 'CMP-9994')),
    pytest.mark.polarion('CMP-9868')(ContainersTestItem(Project, 'CMP-9868')),
    pytest.mark.polarion('CMP-10319')(ContainersTestItem(Template, 'CMP-10319')),
    pytest.mark.polarion('CMP-10410')(ContainersTestItem(Volume, 'CMP-10410'))
]


def check_relationships(instance):
    """Check the relationships linking & data integrity"""
    instance.summary.reload()  # Because sometimes:
    # AttributeError: 'Summary' object has no attribute 'relationships'
    sum_values = instance.summary.relationships.items().values()
    shuffle(sum_values)
    for attr in sum_values:
        if attr.clickable:
            break
    else:
        return  # No clickable object but we still want to pass
    link_value = attr.value
    attr.click()
    if type(link_value) is int:
        rec_total = paginator.rec_total()
        if rec_total != link_value:
            raise Exception('Difference between the value({}) in the relationships table in {}'
                            'to number of records ({}) in the target'
                            'page'.format(link_value, instance.name, rec_total))
    else:
        assert '(Summary)' in summary_title()


@pytest.mark.parametrize('test_item', TEST_ITEMS,
                         ids=[ti.args[1].pretty_id() for ti in TEST_ITEMS])
def test_relationships_tables(provider, test_item):
    """This test verifies the integrity of the Relationships table.
    clicking on each field in the Relationships table takes the user
    to either Summary page where we verify that the field that appears
    in the Relationships table also appears in the Properties table,
    or to the page where the number of rows is equal to the number
    that is displayed in the Relationships table.
    """

    if current_version() < "5.7" and test_item.obj == Template:
        pytest.skip('Templates are not exist in CFME version smaller than 5.7. skipping...')

    rows = navigate_and_get_rows(provider, test_item.obj, 1)
    if not rows:
        pytest.skip('No objects to test for relationships for {}'.format(test_item.obj.__name__))
    row = rows[-1]

    if test_item.obj is Container:
        instance = test_item.obj(row.name.text, row.pod_name.text)
    elif test_item.obj is ImageRegistry:
        instance = test_item.obj(row.host.text, provider)
    elif test_item.obj is Image:
        instance = test_item.obj(row.name.text, row.id.text, provider)
    else:
        instance = test_item.obj(row.name.text, provider)

    check_relationships(instance)


@pytest.mark.polarion('CMP-9934')
def test_container_status_relationships_data_integrity(provider):
    """ This test verifies that the sum of running, waiting and terminated containers
        in the status summary table
        is the same number that appears in the Relationships table containers field
    """
    rows = navigate_and_get_rows(provider, Pod, 3)
    if not rows:
        pytest.skip('No containers found to test. skipping...')
    pod_names = [r.name.text for r in rows]

    for name in pod_names:
        obj = Pod(name, provider)
        assert obj.summary.relationships.containers.value == \
            obj.summary.container_statuses_summary.running.value + \
            obj.summary.container_statuses_summary.waiting.value + \
            obj.summary.container_statuses_summary.terminated.value
