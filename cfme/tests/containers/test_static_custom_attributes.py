import pytest
from utils.version import current_version
from utils import testgen
from cfme.containers.provider.openshift import CustomAttribute

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.7"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

ATTRIBUTES_DATASET = [
    CustomAttribute('exp_date', '2017-01-02', 'Date'),
    CustomAttribute('sales_force_acount', 'ADF231VRWQ1', None),
    CustomAttribute('expected_num_of_nodes', '2', None),
]
VALUE_UPDATES = ['2018-07-12', 'ADF231VRWQ1', '1']


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
    provider.add_custom_attributes(*ATTRIBUTES_DATASET)
    custom_attr_ui = provider.summary.custom_attributes.items()
    for attr in ATTRIBUTES_DATASET:
        assert attr.name in custom_attr_ui
        assert custom_attr_ui[attr.name].text_value == attr.value


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
    # Checking that all ATTRIBUTES_DATASET was added.
    attribs_names = [attr.name for attr in provider.custom_attributes()]
    assert all([attr.name in attribs_names
                for attr in ATTRIBUTES_DATASET])
    EditedAttributes = ATTRIBUTES_DATASET
    for ii, value in enumerate(VALUE_UPDATES):
        EditedAttributes[ii].value = value
    provider.edit_custom_attributes(*EditedAttributes)
    custom_attr_ui = provider.summary.custom_attributes.items()
    for attr in ATTRIBUTES_DATASET:
        assert attr.name in custom_attr_ui
        assert custom_attr_ui[attr.name].text_value == attr.value


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
    # Checking that all ATTRIBUTES_DATASET was added.
    attribs_names = [attr.name for attr in provider.custom_attributes()]
    assert all([attr.name in attribs_names
                for attr in ATTRIBUTES_DATASET])

    provider.delete_custom_attributes()
    if hasattr(provider.summary, 'custom_attributes'):
        for attr in ATTRIBUTES_DATASET:
            assert attr.name not in provider.summary.custom_attributes
