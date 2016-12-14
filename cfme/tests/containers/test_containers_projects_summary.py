import pytest
from cfme.containers.project import Project
from cfme.web_ui import CheckboxTable
from utils import testgen, version
from utils.version import current_version
from utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')


projects_properties_fields = ['Name', 'Creation timestamp', 'Resource version']
projects_relationships_fields_lowest = ['Containers Provider', 'Routes', 'Services', 'Replicators',
                                        'Pods', 'Nodes']
projects_relationships_fields_57 = ['Containers Provider', 'Routes', 'Container Services',
                                    'Replicators', 'Pods', 'Nodes']


projects_relationships_fields_key = ({
    version.LOWEST: projects_relationships_fields_lowest,
    '5.7': projects_relationships_fields_57
})

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")

default_projects = {'default',
'management-infra',
'openshift',
'openshift-infra'}


def config_option():
    return version.pick({version.LOWEST: projects_relationships_fields_lowest,
                         '5.7': projects_relationships_fields_57})

# CMP - 9523


def test_containers_projects_summary_relationships(provider):
    """ Relationships fields tests in Project summary
        This test checks correct population of the Relationships Fields in Containers Projects'
        details menu
        Steps:
            * Goes to Containers -- > Projects menu
            * Go through each Container Project in the menu and check validity of
            Relationships fields
        """
    navigate_to(Project, 'All')
    project_names = [r.name.text for r in list_tbl.rows()]
    for default_project in default_projects:
        assert default_project in project_names
    for name in default_projects:
        for field in config_option():
            print('the tested project is: ' + name)
            print('the tested field is: ' + field)
            obj = Project(name, provider)
            val = obj.get_detail('Relationships', field)
            assert val


def test_containers_projects_summary_properties(provider):
    """ Properties fields tests in Project summary
        This test checks correct population of the Properties Fields in Containers Projects'
        details menu
        Steps:
            * Goes to Containers -- > Projects menu
            * Go through each Container Project in the menu and check validity of Properties fields
        """
    navigate_to(Project, 'All')
    project_names = [r.name.text for r in list_tbl.rows()]
    for default_project in default_projects:
        assert default_project in project_names
    for name in default_projects:
        for field in projects_properties_fields:
            obj = Project(name, provider)
            val = obj.get_detail('Properties', field)
            assert val
