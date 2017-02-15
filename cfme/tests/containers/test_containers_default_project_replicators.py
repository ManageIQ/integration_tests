import pytest
import random

from cfme.web_ui import CheckboxTable
from cfme.containers.provider import ContainersProvider
from cfme.containers.replicator import Replicator
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.6" and provider.version > 3.2),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='module')

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")


REPLICATORS_RELATIONSHIPS_FIELDS = ['Containers Provider', 'Project', 'Pods', 'Nodes',
                                    'My Company Tags']


@pytest.fixture(scope="module")
def replicator(provider):
    navigate_to(Replicator, 'All')
    replicator_name = random.choice([r.name.text for r in list_tbl.rows()])
    return Replicator(replicator_name, provider)


@pytest.mark.parametrize('rel', REPLICATORS_RELATIONSHIPS_FIELDS)
def test_replicators_relationships(replicator, rel):
    """ Default Project Replicator properties and relationships test.
        Steps :
            * Goes to Containers --> Replicators
             * Goes through each Replicator and
               checks each Relationships field.
    """
    assert replicator.get_detail('Relationships', rel)
