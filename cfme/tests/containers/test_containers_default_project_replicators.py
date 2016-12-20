import pytest
import random

from cfme.web_ui import CheckboxTable
from cfme.containers.replicator import Replicator
from itertools import product
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.log import logger
from utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.6" and provider.version > 3.2),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")


REPLICATORS_PROPERTIES_FIELDS = ['Name', 'Creation timestamp', 'Resource version',
                                 'Requested pods', 'Current pods']
REPLICATORS_RELATIONSHIPS_FIELDS = ['Containers Provider', 'Project', 'Pods', 'Nodes',
                                    'My Company Tags']

# CMP - 9531


@pytest.mark.parametrize(('prop', 'rel'), product(REPLICATORS_PROPERTIES_FIELDS,
                                                  REPLICATORS_RELATIONSHIPS_FIELDS))
def test_replicator_properties(provider, prop, rel):
    """ Default Project Replicator properties test
        This test checks the properties fields of each Replicator
        Steps:
            * Goes to Containers --> Replicators
             * Goes through each Replicator and  checks each Properties fields
        """
    navigate_to(Replicator, 'All')
    name = random.choice([r.name.text for r in list_tbl.rows()])
    logger.debug("Chosen the replicator '{}' for inspection.".format(name))
    replicator = Replicator(name, provider)
    assert replicator.get_detail('Properties', ''.join(prop))
    assert replicator.get_detail('Relationships', ''.join(rel))
