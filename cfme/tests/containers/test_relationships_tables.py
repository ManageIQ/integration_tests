import pytest
from random import sample, shuffle
from collections import namedtuple

from cfme.containers.pod import Pod
from cfme.containers.service import Service
from cfme.containers.node import Node, NodeCollection
from cfme.containers.provider import ContainersProvider
from cfme.containers.replicator import Replicator
from cfme.containers.image import Image
from cfme.containers.project import Project
from cfme.containers.template import Template
from cfme.web_ui import CheckboxTable, toolbar as tb, paginator, summary_title
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')

# This is a bit of a hack while only Node has a Collection class
# When refactored for widgets the need for parametrization with tuples will go away
DataSet = namedtuple('DataSet', ['collection', 'object'])

TEST_OBJECTS = [DataSet(None, Pod),
                DataSet(None, Service),
                DataSet(NodeCollection, Node),
                DataSet(None, Replicator),
                DataSet(None, Image),
                DataSet(None, Project)]
rel_values = (0, 'Unknown image source', 'registry.access.redhat.com')

# CMP-9930 CMP-9892 CMP-9965 CMP-9983 CMP-9869 CMP-10321


@pytest.mark.parametrize('cls', sample(TEST_OBJECTS, 4))
def test_relationships_tables(provider, cls):
    """This test verifies the integrity of the Relationships table.
    clicking on each field in the Relationships table takes the user
    to either Summary page where we verify that the field that appears
    in the Relationships table also appears in the Properties table,
    or to the page where the number of rows is equal to the number
    that is displayed in the Relationships table.
    """
    collection = cls.collection if cls.collection is not None else cls.object
    navigate_to(collection, 'All')
    # TODO: When all parametrized classes have widgets, set view and use class properties
    tb.select('List View')
    list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
    cls_instances = [r.name.text for r in list_tbl.rows()]
    cls_instances = sample(cls_instances, min(2, len(cls_instances)))
    for name in cls_instances:
        obj = cls.object(name, provider)
        if current_version() < "5.7" and obj == Template:
            pytest.skip('Templates do not exist in CFME version prior to 5.7, skipping...')
        # TODO: SummaryMixin to be removed from parametrized classes, use widgets instead
        # Basically refactor the this section of the test
        obj.summary.reload()
        sum_values = obj.summary.relationships.items().values()
        shuffle(sum_values)
        for attr in sum_values:
            if attr.clickable:
                break
        link_value = attr.value
        attr.click()
        if type(link_value) is int:
            rec_total = paginator.rec_total()
            if rec_total != link_value:
                pytest.fail('Difference between the value({}) in the relationships table in {}'
                            'to number of records ({}) in the target'
                            'page'.format(link_value, obj.name, rec_total))
        else:
            assert '(Summary)' in summary_title()
