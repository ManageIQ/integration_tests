from random import shuffle, choice
import pytest

from utils.version import current_version
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from cfme.containers.pod import Pod
from cfme.containers.provider import ContainersProvider
from cfme.containers.service import Service
from cfme.containers.node import Node
from cfme.containers.replicator import Replicator
from cfme.containers.image import Image
from cfme.containers.project import Project
from cfme.containers.template import Template
from cfme.web_ui import toolbar as tb, paginator, summary_title
from cfme.containers.container import list_tbl, Container
from cfme.containers.image_registry import ImageRegistry


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


def get_field_name(base_name, table):
    """Since in the relationships table sometimes fields appear in different
    names (i.e. (Image, Images, Container Images, ...)) we use this function
    to find the object we want as it appear in the table, this function
    covers ALL the options
    """
    name_options = [
        base_name,
        base_name + 's',
        'container_{}'.format(base_name),
        'containers_{}'.format(base_name),
        'containers_{}s'.format(base_name),
        'container_{}s'.format(base_name)
    ]
    if base_name.endswith('y'):
        # relevant for image_registry
        name_options.append('{}ies'.format(base_name[:-1]))
    for name in name_options:
        if hasattr(table, name):
            return name


class DataSet(object):
    def __init__(self, obj, expected_fields, polarion_id):
        self.obj = obj
        self.expected_fields = expected_fields
        pytest.mark.polarion(polarion_id)(self)


TEST_OBJECTS = [
    DataSet(ContainersProvider, ['project',
                                 'image_registry',
                                 'replicator',
                                 'pod',
                                 'node',
                                 'image',
                                 'route',
                                 'container',
                                 'service',
                                 'template',
                                 'volume',
                                 'builds'], 'CMP-9851'),
    DataSet(Container, ['provider',
                        'project',
                        'replicator',
                        'pod',
                        'node',
                        'image'], 'CMP-9947'),
    DataSet(Pod, ['provider',
                  'project',
                  'service',
                  'replicator',
                  'container',
                  'node',
                  'image'], 'CMP-9929'),
    DataSet(Service, ['provider',
                      'project',
                      'route',
                      'pod',
                      'node'], 'CMP-10564'),
    DataSet(Node, ['provider',
                   'route',
                   'service',
                   'replicator',
                   'pod',
                   'container',
                   'image'], 'CMP-9962'),
    DataSet(Replicator, ['provider',
                         'project',
                         'pod',
                         'node'], 'CMP-10565'),
    DataSet(Image, ['provider',
                    'image_registry',
                    'project',
                    'pod',
                    'container',
                    'node'], 'CMP-9980'),
    DataSet(ImageRegistry, ['provider',
                            'service',
                            'pod',
                            'container',
                            'image'], 'CMP-9994'),
    DataSet(Project, ['provider',
                      'route',
                      'service',
                      'replicator',
                      'pod',
                      'node',
                      'image',
                      'template'], 'CMP-9868'),
    DataSet(Template, ['provider',
                       'project'], 'CMP-10319')
]


@pytest.mark.parametrize('data_set', TEST_OBJECTS)
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

    navigate_to(data_set.obj, 'All')
    tb.select('List View')
    paginator.results_per_page(1000)
    rows = list(list_tbl.rows())
    if not rows:
        pytest.skip('No objects to test for relationships for {}'.format(data_set.obj.__name__))

    row = choice(rows)
    instance = data_set.obj(row.name.text,
                            (row.pod_name.text if data_set.obj is Container else provider))
    instance.summary.reload()

    missing_fields = []
    for field in data_set.expected_fields:
        if not get_field_name(field, instance.summary.relationships):
            missing_fields.append(field)
    if missing_fields:
        raise Exception('Missing fields in {}({}) relationships table: {}'
                        .format(data_set.obj.__name__, instance.name, missing_fields))

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
