import pytest
from cfme.web_ui import CheckboxTable
from cfme.containers.replicator import Replicator
from itertools import product
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


@pytest.mark.parametrize('prop', product(REPLICATORS_PROPERTIES_FIELDS))
def test_replicators_properties(provider, prop):
    """ Default Project Replicator properties test
        This test checks the properties fields of a Replicator
        Steps :
            * Goes to Containers --> Replicators
             * Goes through each Replicator and  checks each Properties fields
        """
    navigate_to(Replicator, 'All')
    replicator_name = [r.name.text for r in list_tbl.rows()]
    for name in replicator_name:
        obj = Replicator(name, provider)
        assert obj.get_detail('Properties', ''.join(prop))
        break


@pytest.mark.parametrize('rel', product(REPLICATORS_RELATIONSHIPS_FIELDS))
def test_replicators_relationships(provider, rel):
    """ Default Project Replicator properties test
        This test checks the properties fields of a Replicator
        Steps:
            * Goes to Containers --> Replicators
             * Goes through each Replicator and  checks each Relationship fields
        """
    navigate_to(Replicator, 'All')
    replicator_name = [r.name.text for r in list_tbl.rows()]
    for name in replicator_name:
        obj = Replicator(name, provider)
        assert obj.get_detail('Relationships', ''.join(rel))
        break
