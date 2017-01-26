import pytest

from manageiq_client.api import APIException

from utils.version import current_version
from utils import testgen
from cfme.containers.provider import ContainersProvider
from cfme.containers.provider.openshift import CustomAttribute

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.7"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')

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
    edited_attribs = ATTRIBUTES_DATASET
    for ii, value in enumerate(VALUE_UPDATES):
        edited_attribs[ii].value = value
    provider.edit_custom_attributes(*edited_attribs)
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


# CMP-10303

def test_add_attribute_with_empty_name(provider):
    """Tests adding of static custom attributes with empty field
    Steps:
        * add the static custom attribute with name "" (API)
        * Go to provider summary page
    Expected results:
        * You should get an error
        * You should not see this attribute in the custom  attributes table
    """
    try:
        provider.add_custom_attributes(
            CustomAttribute('', "17")
        )
        pytest.fail('You have added custom attribute with empty name'
                    'and didn\'t get an error!')
    except APIException:
        pass

    if hasattr(provider.summary, 'custom_attributes'):
        assert "" not in provider.summary.custom_attributes


def test_add_date_value_with_wrong_value(provider):
    ca = CustomAttribute('nondate', "koko", 'Date')
    try:
        provider.add_custom_attributes(ca)
        pytest.fail('You have added custom attribute of type'
                    '{} with value of {} and didn\'t get an error!'
                    .format(ca.field_type, ca.value))
    except APIException:
        pass

    if hasattr(provider.summary, 'custom_attributes'):
        assert 'nondate' not in provider.summary.custom_attributes
