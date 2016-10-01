import pytest

from cfme.containers.pod import Pod
from cfme.containers.service import Service
from cfme.containers.node import Node
from cfme.containers.replicator import Replicator
from cfme.containers.image import Image
from cfme.containers.project import Project
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable, paginator, toolbar as tb
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.log import logger
from cfme.cloud.availability_zone import details_page


pytestmark = [pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")


TEST_OBJECTS = [Pod, Service, Node, Replicator, Image, Project]

rel_values = (0, 'Unknown image source', 'registry.access.redhat.com')


# 9930 # 9892 # 9965 # 9983 # 9869


@pytest.mark.parametrize('cls', TEST_OBJECTS)
def test_relationships_tables(provider, cls):
    """  This module verifies the integrity of the Relationships table.
               clicking on each field in the Relationships table takes the user
              to either Summary page where we verify that the field that appears
             in the Relationships table also appears in the Properties table,
            or to the page where the number of rows is equal to the number
           that is displayed in the Relationships table.
    """
    navigate_to(cls, 'All')
    tb.select('List View')
    list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
    cls_instances = [r.name.text for r in list_tbl.rows()]
    cls_instances_revised = [ch for ch in cls_instances
                             if 'nginx' not in ch and not ch.startswith('metrics')]
    for name in cls_instances_revised:
        navigate_to(cls, 'All')
        obj = cls(name, provider)
        rel_tbl = obj.summary.groups()['relationships']
        keys = [key for key in rel_tbl.keys]
        for key in keys:
            # reload summary to prevent StaleElementReferenceException:
            obj.summary.reload()
            rel_tbl = obj.summary.groups()['relationships']
            element = getattr(rel_tbl, key)
            value = element.value
            if value in rel_values:
                continue
            sel.click(element)

            try:
                value = int(value)
            except ValueError:
                assert value == details_page.infoblock.text(
                    'Properties', 'Name')
            else:
                # best effort to include all items from rel on one page
                if paginator.page_controls_exist():
                    paginator.results_per_page(1000)
                else:
                    logger.warning(
                        'Unable to increase results per page, '
                        'assertion against number of rows may fail.')
                assert len([r for r in list_tbl.rows()]) == value
