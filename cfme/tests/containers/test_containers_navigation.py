import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import summary_title as st
from cfme.web_ui import InfoBlock

from cfme.configure import settings  # noqa
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')


# CMP-9949 CMP-9947
if current_version() != "upstream":
    RELATIONSHIP_TITLES = {
        'Projects': 'All Projects',
        'Routes': 'All Routes',
        'Services': 'All Services',
        'Replicators': 'All Replicators',
        'Pods': 'All Pods',
        'Containers': 'All Containers',
        'Nodes': 'All Nodes',
        'Images': 'All Images',
        'Container Builds': 'All Builds',
        #    Bug 1359850 - When no relationship exist, the row with the relationship
        #    is not clickable.
        #    'Volumes': 'All Volumes',
        #    'Image Registries': 'All Image Registries',
    }
else:
    RELATIONSHIP_TITLES = {
        'Projects': 'All Projects',
        'Routes': 'All Routes',
        'Container Services': 'All Services',
        'Replicators': 'All Replicators',
        'Pods': 'All Pods',
        'Containers': 'All Containers',
        'Nodes': 'All Nodes',
        'Container Images': 'All Images',
        'Container Builds': 'All Builds',
        #    Bug 1359850 - When no relationship exist, the row with the relationship
        #    is not clickable.
        #    'Volumes': 'All Volumes',
        #    'Image Registries': 'All Image Registries',
    }


@pytest.mark.parametrize(('relationship', 'relship_title'),
                         RELATIONSHIP_TITLES.items())
def test_containers_providers_relationships_navigation(provider, relationship, relship_title):
    sel.force_navigate('containers_providers')
    provider.navigate()
    ib = InfoBlock('Relationships', relationship)
    ib.element.click()
    assert st() == '{} ({})'.format(provider.name, relship_title)
