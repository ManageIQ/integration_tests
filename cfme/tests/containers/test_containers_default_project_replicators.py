import pytest
import random

from cfme.web_ui import CheckboxTable
from cfme.containers.replicator import Replicator
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
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
def test_replicators(provider):
    """ Default Project Replicator properties and relationships test.
        Steps :
            * Goes to Containers --> Replicators
             * Goes through each Replicator and
               checks each Properties and Relationships field.
        """
    navigate_to(Replicator, 'All')
    replicator_name = random.choice([r.name.text for r in list_tbl.rows()])
    obj = Replicator(replicator_name, provider)
    for prop in REPLICATORS_PROPERTIES_FIELDS:
        assert obj.get_detail('Properties', prop)
    for rel in REPLICATORS_RELATIONSHIPS_FIELDS:
        assert obj.get_detail('Relationships', rel)
