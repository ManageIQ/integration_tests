import pytest
from itertools import product
from cfme.fixtures import pytest_selenium as sel
from cfme.containers.project import Project
from cfme.web_ui import CheckboxTable
from utils import testgen
from utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')


PROJECTS_PROPERTIES_FIELDS = ['Name', 'Creation timestamp', 'Resource version']
PROJECTS_RELATIONSHIPS_FIELDS = ['Containers Provider', 'Routes', 'Services', 'Replicators',
                                 'Pods', 'Nodes']

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")


# CMP - 9523


@pytest.mark.parametrize('projects_relationships_fields', product(PROJECTS_RELATIONSHIPS_FIELDS))
def test_containers_projects_summary_relationships(provider, projects_relationships_fields):
    """ Containers Projects details page > Relationships fields
        This test checks correct population of the Relationships Fields in Containers Projects'
        details menu
        Steps:
            * Goes to Containers -- > Projects menu
            * Go through each Container Project in the menu and check validity of
            Relationships fields
        """
    sel.force_navigate('containers_projects')
    project_name = [r.name.text for r in list_tbl.rows()]
    for name in project_name:
        obj = Project(name, provider)
        val = obj.get_detail('Relationships', ''.join(projects_relationships_fields))
        assert val


@pytest.mark.parametrize('projects_properties_fields', product(PROJECTS_PROPERTIES_FIELDS))
def test_containers_projects_summary_properties(provider, projects_properties_fields):
    """ Containers Projects details page > Properties fields
        This test checks correct population of the Properties Fields in Containers Projects'
        details menu
        Steps:
            * Goes to Containers -- > Projects menu
            * Go through each Container Project in the menu and check validity of Properties fields
        """
    sel.force_navigate('containers_projects')
    project_name = [r.name.text for r in list_tbl.rows()]
    for name in project_name:
        obj = Project(name, provider)
        val = obj.get_detail('Properties', ''.join(projects_properties_fields))
        assert val
