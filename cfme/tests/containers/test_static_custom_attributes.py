from string import digits, ascii_letters
from random import choice
from os import path
import re
import pytest

from manageiq_client.api import APIException

from cfme.containers.provider import ContainersProvider, refresh_and_navigate
from cfme.containers.provider.openshift import CustomAttribute

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2),
    pytest.mark.provider([ContainersProvider], scope='function')
]


def get_random_string(length):
    valid_chars = digits + ascii_letters + ' !@#$%^&*()'
    out = ''.join([choice(valid_chars) for _ in xrange(length)])
    return re.sub('\s+', ' ', out)


ATTRIBUTES_DATASET = [
    CustomAttribute('exp date', '2017-01-02', 'Date'),
    CustomAttribute('sales force acount', 'ADF231VRWQ1', None),
    CustomAttribute('expected num of nodes', '2', None)
]
VALUE_UPDATES = ['2018-07-12', 'ADF231VRWQ1', '1']


# TODO: Fixturize tests


@pytest.mark.polarion('CMP-10281')
def test_add_static_custom_attributes(provider):
    """Tests adding of static custom attributes to provider
    Steps:
        * Add static custom attributes (API)
        * Go to provider summary page
    Expected results:
        * The attributes was successfully added
    """

    provider.add_custom_attributes(*ATTRIBUTES_DATASET)
    view = refresh_and_navigate(provider, 'Details')
    custom_attr_ui = view.entities.custom_attributes.read()
    for attr in ATTRIBUTES_DATASET:
        assert attr.name in custom_attr_ui
        assert custom_attr_ui[attr.name] == attr.value


@pytest.mark.polarion('CMP-10286')
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

    edited_attribs = ATTRIBUTES_DATASET
    for ii, value in enumerate(VALUE_UPDATES):
        edited_attribs[ii].value = value
    provider.edit_custom_attributes(*edited_attribs)
    view = refresh_and_navigate(provider, 'Details')
    custom_attr_ui = view.entities.custom_attributes.read()
    for attr in ATTRIBUTES_DATASET:
        assert attr.name in custom_attr_ui
        assert custom_attr_ui[attr.name] == attr.value


@pytest.mark.polarion('CMP-10285')
def test_delete_static_custom_attributes(provider):
    """Tests deleting of static custom attributes from provider
    Steps:
        * Delete the static custom attributes that recently added (API)
        * Go to provider summary page
    Expected results:
        * The attributes was successfully deleted
        (you should not see a custom attributes table)
    """

    provider.delete_custom_attributes(*ATTRIBUTES_DATASET)
    view = refresh_and_navigate(provider, 'Details')
    if view.entities.custom_attributes.is_displayed:
        for attr in ATTRIBUTES_DATASET:
            assert attr.name not in view.entities.custom_attributes


@pytest.mark.polarion('CMP-10303')
def test_add_attribute_with_empty_name(provider):
    """Tests adding of static custom attributes with empty field
    Steps:
        * add the static custom attribute with name "" (API)
        * Go to provider summary page
    Expected results:
        * You should get an error
        * You should not see this attribute in the custom  attributes table
    """
    with pytest.raises(APIException):
        provider.add_custom_attributes(
            CustomAttribute('', "17")
        )
        pytest.fail('You have added custom attribute with empty name'
                    'and didn\'t get an error!')
    view = refresh_and_navigate(provider, 'Details')
    if view.entities.custom_attributes.is_displayed:
        assert "" not in view.entities.custom_attributes.read()


@pytest.mark.polarion('CMP-10404')
def test_add_date_attr_with_wrong_value(provider):
    """Trying to add attribute of type date with non-date value"""
    ca = CustomAttribute('nondate', "koko", 'Date')
    with pytest.raises(APIException):
        provider.add_custom_attributes(ca)
        pytest.fail('You have added custom attribute of type'
                    '{} with value of {} and didn\'t get an error!'
                    .format(ca.field_type, ca.value))
    view = refresh_and_navigate(provider, 'Details')
    if view.entities.custom_attributes.is_displayed:
        assert 'nondate' not in view.entities.custom_attributes.read()


@pytest.mark.polarion('CMP-10405')
def test_edit_non_exist_attribute(provider):
    """Trying to edit non-exist attribute"""
    ca = choice(ATTRIBUTES_DATASET)
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
    with pytest.raises(APIException):
        provider.appliance.rest_api.post(
            path.join(provider.href(), 'custom_attributes'), **payload)
        pytest.fail('You tried to edit a non-exist custom attribute'
                    '({}) and didn\'t get an error!'
                    .format(ca.value))


@pytest.mark.polarion('CMP-10543')
def test_delete_non_exist_attribute(provider):

    ca = choice(ATTRIBUTES_DATASET)
    with pytest.raises(APIException):
        provider.delete_custom_attributes(ca)
        pytest.fail('You tried to delete a non-exist custom attribute'
                    '({}) and didn\'t get an error!'
                    .format(ca.value))


@pytest.mark.polarion('CMP-10542')
def test_add_already_exist_attribute(provider):
    ca = choice(ATTRIBUTES_DATASET)
    provider.add_custom_attributes(ca)


@pytest.mark.polarion('CMP-10540')
def test_very_long_name_with_special_characters(provider):
    ca = CustomAttribute(get_random_string(1000), 'very_long_name', None)
    provider.add_custom_attributes(ca)
    view = refresh_and_navigate(provider, 'Details')
    assert ca.name in view.entities.custom_attributes.read()
    provider.delete_custom_attributes(ca)


@pytest.mark.polarion('CMP-10541')
def test_very_long_value_with_special_characters(provider):
    ca = CustomAttribute('very_long_value', get_random_string(1000), None)
    provider.add_custom_attributes(ca)
    view = refresh_and_navigate(provider, 'Details')
    assert ca.value == view.entities.custom_attributes.read().get('very_long_value')
    provider.delete_custom_attributes(ca)
