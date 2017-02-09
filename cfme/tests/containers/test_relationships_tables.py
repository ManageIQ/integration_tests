from random import sample, shuffle
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
from cfme.web_ui import CheckboxTable, toolbar as tb, paginator, summary_title


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


TEST_OBJECTS = [Pod, Service, Node, Replicator, Image, Project, Template]


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
    if current_version() < "5.7" and cls == Template:
        pytest.skip('Templates are not exist in CFME version smaller than 5.7. skipping...')
    navigate_to(cls, 'All')
    tb.select('List View')
    list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
    names = [r.name.text for r in list_tbl.rows()]
    names = sample(names, min(2, len(names)))
    for name in names:
        obj = cls(name, provider)
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
