import pytest
import random

from cfme.web_ui import CheckboxTable
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version
from cfme.containers.template import Template


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < 5.7),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(3)]
pytest_generate_tests = testgen.generate(
    testgen.containers_providers, scope='function')

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")


TEMPLATE_RELATIONSHIP_FIELDS = ['Containers Provider', 'Project']
TEMPLATE_PROPERTES_FIELDS = ['Name', 'Creation timestamp', 'Resource version']


@pytest.fixture(scope="function")
def template(provider):
    navigate_to(Template, 'All')
    template_name = random.choice([r.name.text for r in list_tbl.rows()])
    return Template(template_name, provider)


# CMP-10321
@pytest.mark.parametrize('rel', TEMPLATE_RELATIONSHIP_FIELDS)
def test_containers_templates_relationships(template, rel):
    """ This test checks the Relationship fields of Container Templates
        under Container Providers
       Steps:
           * Navigate to Compute -> Containers -> Container Templates.
           Verify there's a list of Templates
           * Select a random Container Template and check its' Relationships fields
       """
    assert template.get_detail('Relationships', rel)


@pytest.mark.parametrize('prop', TEMPLATE_PROPERTES_FIELDS)
def test_containers_templates_properties(template, prop):
    """ This test checks the Properties fields of Container Templates
        under Container Providers
       Steps:
           * Navigate to Compute -> Containers -> Container Templates.
           Verify there's a list of Templates
           * Select a random Container Template and check its' Properties fields
       """
    assert template.get_detail('Properties', prop)
