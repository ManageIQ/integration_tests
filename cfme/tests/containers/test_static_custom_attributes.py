import pytest
from utils.version import current_version
from utils import testgen

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.7"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

attributes_dataset = {
    'names': ['exp_date', 'sales_force_acount', 'expected_num_of_nodes'],
    'values': ['2017-01-02', 'ADF231VRWQ1', '2'],
    'values_update': ['2018-07-12', 'ADF231VRWQ1', '1'],
    'field_types': ['Date', None, None]
}


# CMP-10281

def test_add_static_custom_attributes(provider):
    """Tests adding of static custom attributes to provider
    Steps:
        * Add static custom attributes (API)
        * Go to provider summary page
    Expected results:
        * The attributes was successfully added
    """
    assert not provider.custom_attributes()
    provider.add_custom_attributes(attributes_dataset['names'],
                                   attributes_dataset['values'],
                                   attributes_dataset['field_types'])
    custom_attr_ui = provider.summary.custom_attributes.items()
    for name, value in zip(attributes_dataset['names'],
                           attributes_dataset['values']):
        assert name in custom_attr_ui
        assert custom_attr_ui[name].text_value == value


# CMP-10286

def test_edit_static_custom_attributes(provider):
    """Tests editing of static custom attributes from provider
    Prerequisite:
        * test_add_static_custom_attributes passed.
    Steps:
        * Edit (update) the static custom attributes (API)
        * Go to provider summary page
    Expected results:
        * The attributes was successfully updated to the new values
    """
    # Checking that all attributes_dataset was added.
    attribs_api = provider.custom_attributes()
    assert all([name in attribs_api
                for name in attributes_dataset['names']])

    provider.edit_custom_attributes(attributes_dataset['names'],
                                    attributes_dataset['values_update'])
    custom_attr_ui = provider.summary.custom_attributes.items()
    for name, value in zip(attributes_dataset['names'],
                           attributes_dataset['values_update']):
        assert name in custom_attr_ui
        assert custom_attr_ui[name].text_value == value


# CMP-10285

def test_delete_static_custom_attributes(provider):
    """Tests deleting of static custom attributes from provider
    Steps:
        * Delete the static custom attributes that recently added (API)
        * Go to provider summary page
    Expected results:
        * The attributes was successfully deleted
        (you should not see a custom attributes table)
    """
    # Checking that all attributes_dataset was added.
    attribs_api = provider.custom_attributes()
    assert all([name in attribs_api
                for name in attributes_dataset['names']])

    provider.delete_custom_attributes(attributes_dataset['names'])
    if hasattr(provider.summary, 'custom_attributes'):
        for name in attributes_dataset['names']:
            assert name not in provider.summary.custom_attributes
