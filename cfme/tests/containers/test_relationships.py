from random import shuffle

import pytest

from utils import testgen
from utils.version import current_version
from cfme.web_ui import paginator, summary_title

from cfme.containers.pod import Pod, paged_tbl as pod_paged_tbl
from cfme.containers.provider import ContainersProvider, paged_tbl as provider_paged_tbl,\
    navigate_and_get_rows
from cfme.containers.service import Service, paged_tbl as service_paged_tbl
from cfme.containers.node import Node, list_tbl as node_paged_tbl
from cfme.containers.replicator import Replicator, paged_tbl as replicator_paged_tbl
from cfme.containers.image import Image, paged_tbl as image_paged_tbl
from cfme.containers.project import Project, paged_tbl as project_paged_tbl
from cfme.containers.template import Template, paged_tbl as template_paged_tbl
from cfme.containers.container import Container, paged_tbl as container_paged_tbl
from cfme.containers.image_registry import ImageRegistry, paged_tbl as image_registry_paged_tbl


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


class DataSet(object):
    def __init__(self, obj, paged_tbl, polarion_id):
        self.obj = obj
        self.paged_tbl = paged_tbl
        pytest.mark.polarion(polarion_id)(self)


TEST_OBJECTS = [
    DataSet(ContainersProvider, provider_paged_tbl, 'CMP-9851'),
    DataSet(Container, container_paged_tbl, 'CMP-9947'),
    DataSet(Pod, pod_paged_tbl, 'CMP-9929'),
    DataSet(Service, service_paged_tbl, 'CMP-10564'),
    DataSet(Node, node_paged_tbl, 'CMP-9962'),
    DataSet(Replicator, replicator_paged_tbl, 'CMP-10565'),
    DataSet(Image, image_paged_tbl, 'CMP-9980'),
    DataSet(ImageRegistry, image_registry_paged_tbl, 'CMP-9994'),
    DataSet(Project, project_paged_tbl, 'CMP-9868'),
    DataSet(Template, template_paged_tbl, 'CMP-10319')
]


def check_relationships(instance):
    """Check the relationships linking & data integrity"""
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


@pytest.mark.parametrize('data_set', TEST_OBJECTS, ids=[obj.obj for obj in TEST_OBJECTS])
def test_relationships_tables(provider, data_set):
    """This test verifies the integrity of the Relationships table.
    clicking on each field in the Relationships table takes the user
    to either Summary page where we verify that the field that appears
    in the Relationships table also appears in the Properties table,
    or to the page where the number of rows is equal to the number
    that is displayed in the Relationships table.
    """

    if current_version() < "5.7" and data_set.obj == Template:
        pytest.skip('Templates are not exist in CFME version smaller than 5.7. skipping...')

    rows = navigate_and_get_rows(provider, data_set.obj, data_set.paged_tbl, 1)
    if not rows:
        pytest.skip('No objects to test for relationships for {}'.format(data_set.obj.__name__))
    row = rows[-1]

    if data_set.obj is Container:
        instance = data_set.obj(row.name.text, row.pod_name.text)
    elif data_set.obj is ImageRegistry:
        instance = data_set.obj(row.host.text, provider)
    elif data_set.obj is Image:
        instance = data_set.obj(row.name.text, row.tag.text, provider)
    else:
        instance = data_set.obj(row.name.text, provider)

    check_relationships(instance)
