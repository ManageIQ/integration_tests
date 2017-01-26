from string import digits, ascii_letters
from random import choice
from traceback import format_exception_only
from os import path
import sys
import inspect
import re
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


def get_random_string(length):
    valid_chars = digits + ascii_letters + ' !@#$%^&*()'
    out = ''.join([choice(valid_chars) for _ in xrange(length)])
    return re.sub('\s+', ' ', out)


ATTRIBUTES_DATASET = [
    CustomAttribute('exp_date', '2017-01-02', 'Date'),
    CustomAttribute('sales_force_acount', 'ADF231VRWQ1', None),
    CustomAttribute('expected_num_of_nodes', '2', None)
]
VALUE_UPDATES = ['2018-07-12', 'ADF231VRWQ1', '1']


def setup_dataset(provider, verify_exists=False):
    """Either delete or add (verify_exists) the dataset according
    to the test prerequisites, skipping test if failed
    """
    try:
        current_attrs_names = [attr.name for attr in provider.custom_attributes()]
        if verify_exists:
            attrs_to_add = [attr for attr in ATTRIBUTES_DATASET
                            if attr.name not in current_attrs_names]
            if attrs_to_add:
                provider.add_custom_attributes(*attrs_to_add)
        else:
            attrs_to_delete = [attr for attr in ATTRIBUTES_DATASET
                               if attr.name in current_attrs_names]
            if attrs_to_delete:
                provider.delete_custom_attributes(*attrs_to_delete)
    except:
        pytest.skip('Could not setup prerequisites for {}:\n{}'
                    .format(inspect.stack()[1][3],
                            format_exception_only(sys.exc_type, sys.exc_value)[0]))


# CMP-10281

def test_add_static_custom_attributes(provider):
    """Tests adding of static custom attributes to provider
    Steps:
        * Add static custom attributes (API)
        * Go to provider summary page
    Expected results:
        * The attributes was successfully added
    """
    setup_dataset(provider, verify_exists=False)

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
    setup_dataset(provider, verify_exists=True)

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
    setup_dataset(provider, verify_exists=True)

    provider.delete_custom_attributes(*ATTRIBUTES_DATASET)
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


# CMP-10404

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


# CMP-10405

def test_edit_non_exist_attribute(provider):
    setup_dataset(provider, verify_exists=False)

    ca = choice(ATTRIBUTES_DATASET)
    try:
        # Note: we need to implement it inside the test instead of using
        #       the API (provider.edit_custom_attributes) in order to
        #       specify the href and yield the exception
        payload = {
            "action": "edit",
            "resources": [{
                "href": '{}/custom_attributes/9876543210000000'
                        .format(provider.href()),
                "value": ca.value
            }]}
        provider.appliance.rest_api.post(
            path.join(provider.href(), 'custom_attributes'), **payload)
        pytest.fail('You tried to edit a non-exist custom attribute'
                    '({}) and didn\'t get an error!'
                    .format(ca.value))
    except APIException:
        pass


# CMP-10543

def test_delete_non_exist_attribute(provider):
    setup_dataset(provider, verify_exists=False)

    ca = choice(ATTRIBUTES_DATASET)
    try:
        provider.delete_custom_attributes(ca)
        pytest.fail('You tried to delete a non-exist custom attribute'
                    '({}) and didn\'t get an error!'
                    .format(ca.value))
    except APIException:
        pass


# CMP-10542

@pytest.mark.meta(blockers=[1416797])
def test_add_already_exist_attribute(provider):
    setup_dataset(provider, verify_exists=True)
    ca = choice(ATTRIBUTES_DATASET)
    try:
        provider.add_custom_attributes(ca)
        pytest.fail('You tried to add a custom attribute that already exists'
                    '({}) and didn\'t get an error!'
                    .format(ca.value))
    except APIException:
        pass


# CMP-10540

def test_very_long_name_with_special_characters(provider):
    ca = CustomAttribute(get_random_string(1000), 'very_long_name', None)
    provider.add_custom_attributes(ca)
    provider.summary.reload()
    assert ca.name in provider.summary.custom_attributes.raw_keys
    provider.delete_custom_attributes(ca)


# CMP-10541

def test_very_long_value_with_special_characters(provider):
    ca = CustomAttribute('very_long_value', get_random_string(1000), None)
    provider.add_custom_attributes(ca)
    provider.summary.reload()
    assert ca.value == provider.summary.custom_attributes.very_long_value.value
    provider.delete_custom_attributes(ca)
