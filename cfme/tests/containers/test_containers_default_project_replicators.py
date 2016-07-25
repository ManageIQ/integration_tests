import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable
from cfme.containers.replicator import Replicator
from itertools import product
from utils import testgen
from utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(
        (lambda: current_version() < "5.6") or (lambda provider: provider.version < 3.2)),
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


@pytest.mark.parametrize('replicators_properties_fields', product(REPLICATORS_PROPERTIES_FIELDS))
def test_containers_replicators_properties(provider, replicators_properties_fields):
    """ Default Project Replicator properties test
        This test checks the properties fields of each Replicator
        Steps:
            * Goes to Containers --> Replicators
            * Makes sure "router-1" is one of the existing Replicators
             * Goes through each Replicator and checks each Properties fields
        """
    sel.force_navigate('containers_replicators')
    replicator_name = [r.name.text for r in list_tbl.rows()]
    assert "router-1" in replicator_name
    for name in replicator_name:
        obj = Replicator(name, provider)
        val = obj.get_detail('Properties', ''.join(replicators_properties_fields))
        assert val


@pytest.mark.parametrize('replicators_relationships_fields',
                         product(REPLICATORS_RELATIONSHIPS_FIELDS))
def test_containers_replicators_relationships(
        provider, replicators_relationships_fields):
    """ Default Project Replicator properties test
        This test checks the properties fields of each Replicator
        Steps:
            * Goes to Containers --> Replicators
             * Goes through each Replicator and checks each Relationships fields
        """
    sel.force_navigate('containers_replicators')
    replicator_name = [r.name.text for r in list_tbl.rows()]
    for name in replicator_name:
        obj = Replicator(name, provider)
        val = obj.get_detail('Relationships', ''.join(replicators_relationships_fields))
        assert val
