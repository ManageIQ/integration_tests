import pytest
from utils.version import current_version
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from cfme.containers.pod import Pod, match_page as pod_match_page
from cfme.containers.provider import ContainersProvider
from cfme.containers.service import Service, match_page as service_match_page
from cfme.containers.node import Node, match_page as node_match_page
from cfme.containers.replicator import Replicator, match_page as replicator_match_page
from cfme.containers.image import Image, match_page as image_match_page
from cfme.containers.project import Project, match_page as project_match_page
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable, toolbar as tb
from random import sample
from collections import namedtuple


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


DataSet = namedtuple('DataSet', ['object', 'match_page'])

TEST_OBJECTS = [DataSet(Pod, pod_match_page),
                DataSet(Service, service_match_page),
                DataSet(Node, node_match_page),
                DataSet(Replicator, replicator_match_page),
                DataSet(Image, image_match_page),
                DataSet(Project, project_match_page)]
rel_values = (0, 'Unknown image source', 'registry.access.redhat.com')

# CMP-9930 CMP-9892 CMP-9965 CMP-9983 CMP-9869


@pytest.mark.parametrize('cls', TEST_OBJECTS)
def test_relationships_tables(provider, cls):
    """This module verifies the integrity of the Relationships table.
    clicking on each field in the Relationships table takes the user
    to either Summary page where we verify that the field that appears
    in the Relationships table also appears in the Properties table,
    or to the page where the number of rows is equal to the number
    that is displayed in the Relationships table.
    """
    navigate_to(cls.object, 'All')
    tb.select('List View')
    list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
    cls_instances = [r.name.text for r in list_tbl.rows()]
    cls_instances = sample(cls_instances, min(2, len(cls_instances)))
    for name in cls_instances:
        obj = cls.object(name, provider)
        obj.summary.reload()
        keys = sample(obj.summary.relationships.keys,
                      min(1, len(obj.summary.relationships.keys)))
        for key in keys:
            # reload summary to prevent StaleElementReferenceException:
            obj.summary.reload()
            element = getattr(obj.summary.relationships, key)
            if element.value in rel_values:
                continue
            sel.click(element)
            # TODO: find a better indication that we are in the right page:
            sel.is_displayed_text('{} (Summary)'.format(element.text_value))
