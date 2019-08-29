import re
from copy import deepcopy
from os import path
from random import choice
from string import ascii_letters
from string import digits

import pytest
from manageiq_client.api import APIException

from cfme import test_requirements
from cfme.containers.provider import ContainersProvider
from cfme.containers.provider.openshift import CustomAttribute
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2),
    pytest.mark.provider([ContainersProvider], scope='function'),
    test_requirements.containers
]


def get_random_string(length):
    valid_chars = digits + ascii_letters + ' !@#$%^&*()'
    out = ''.join([choice(valid_chars) for _ in range(length)])
    return re.sub(r'\s+', ' ', out)


ATTRIBUTES_DATASET = [
    CustomAttribute('exp date', '2017-01-02', 'Date'),
    CustomAttribute('sales force acount', 'ADF231VRWQ1', None),
    CustomAttribute('expected num of nodes', '2', None)
]
VALUE_UPDATES = ['2018-07-12', 'ADF231VRWQ1', '1']

# TODO These should be factored into a single CRUD test


@pytest.fixture(scope='function')
def add_delete_custom_attributes(provider):
    provider.add_custom_attributes(*ATTRIBUTES_DATASET)
    view = navigate_to(provider, 'Details', force=True)
    assert view.entities.summary('Custom Attributes').is_displayed
    yield
    try:
        provider.delete_custom_attributes(*ATTRIBUTES_DATASET)
    except APIException:
        logger.info("No custom attributes to delete")


def test_add_static_custom_attributes(add_delete_custom_attributes, provider):
    """Tests adding of static custom attributes to provider
    Steps:
        * Add static custom attributes (API)
        * Go to provider summary page
    Expected results:
        * The attributes was successfully added

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """

    view = navigate_to(provider, 'Details', force=True)
    custom_attr_ui = view.entities.summary('Custom Attributes')
    for attr in ATTRIBUTES_DATASET:
        assert attr.name in custom_attr_ui.fields
        assert custom_attr_ui.get_text_of(attr.name) == attr.value


def test_edit_static_custom_attributes(provider):
    """Tests editing of static custom attributes from provider
    Prerequisite:
        * test_add_static_custom_attributes passed.
    Steps:
        * Edit (update) the static custom attributes (API)
        * Go to provider summary page
    Expected results:
        * The attributes was successfully updated to the new values

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """

    provider.add_custom_attributes(*ATTRIBUTES_DATASET)
    edited_attribs = deepcopy(ATTRIBUTES_DATASET)
    for ii, value in enumerate(VALUE_UPDATES):
        edited_attribs[ii].value = value
    provider.edit_custom_attributes(*edited_attribs)
    view = navigate_to(provider, 'Details', force=True)
    custom_attr_ui = view.entities.summary('Custom Attributes')
    for attr in edited_attribs:
        assert attr.name in custom_attr_ui.fields
        assert custom_attr_ui.get_text_of(attr.name) == attr.value
    provider.delete_custom_attributes(*edited_attribs)


def test_delete_static_custom_attributes(add_delete_custom_attributes, request, provider):
    """Tests deleting of static custom attributes from provider
    Steps:
        * Delete the static custom attributes that recently added (API)
        * Go to provider summary page
    Expected results:
        * The attributes was successfully deleted
        (you should not see a custom attributes table)

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """

    provider.delete_custom_attributes(*ATTRIBUTES_DATASET)
    view = navigate_to(provider, 'Details', force=True)
    if view.entities.summary('Custom Attributes').is_displayed:
        for attr in ATTRIBUTES_DATASET:
            assert attr.name not in view.entities.summary('Custom Attributes').fields
    else:
        logger.info("No custom attributes table to check")
        assert True

    ca = CustomAttribute('test_value', 'This is a test', None)
    request.addfinalizer(lambda: provider.delete_custom_attributes(ca))
    provider.add_custom_attributes(ca)
    provider.add_custom_attributes(*ATTRIBUTES_DATASET)
    provider.browser.refresh()
    for attr in ATTRIBUTES_DATASET:
        assert attr.name in view.entities.summary('Custom Attributes').fields
        assert view.entities.summary('Custom Attributes').get_text_of(attr.name) == attr.value
    provider.delete_custom_attributes(*ATTRIBUTES_DATASET)
    provider.browser.refresh()
    if view.entities.summary('Custom Attributes').is_displayed:
        for attr in ATTRIBUTES_DATASET:
            assert attr.name not in view.entities.summary('Custom Attributes').fields
    else:
        logger.info("Custom Attributes Table does not exist. Expecting it to exist")
        assert False


def test_add_attribute_with_empty_name(provider):
    """Tests adding of static custom attributes with empty field
    Steps:
        * add the static custom attribute with name "" (API)
        * Go to provider summary page
    Expected results:
        * You should get an error
        * You should not see this attribute in the custom  attributes table

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    with pytest.raises(APIException):
        provider.add_custom_attributes(
            CustomAttribute('', "17")
        )
        pytest.fail('You have added custom attribute with empty name'
                    'and didn\'t get an error!')
    view = navigate_to(provider, 'Details', force=True)
    if view.entities.summary('Custom Attributes').is_displayed:
        assert "" not in view.entities.summary('Custom Attributes').fields


def test_add_date_attr_with_wrong_value(provider):
    """Trying to add attribute of type date with non-date value

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    ca = CustomAttribute('nondate', "koko", 'Date')
    with pytest.raises(APIException):
        provider.add_custom_attributes(ca)
        pytest.fail('You have added custom attribute of type'
                    '{} with value of {} and didn\'t get an error!'
                    .format(ca.field_type, ca.value))
    view = navigate_to(provider, 'Details', force=True)
    if view.entities.summary('Custom Attributes').is_displayed:
        assert 'nondate' not in view.entities.summary('Custom Attributes').fields


def test_edit_non_exist_attribute(provider):
    """Trying to edit non-exist attribute

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
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


def test_delete_non_exist_attribute(provider):

    """
    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    ca = choice(ATTRIBUTES_DATASET)
    with pytest.raises(APIException):
        provider.delete_custom_attributes(ca)
        pytest.fail('You tried to delete a non-exist custom attribute'
                    '({}) and didn\'t get an error!'
                    .format(ca.value))


def test_add_already_exist_attribute(provider):
    """
    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    ca = choice(ATTRIBUTES_DATASET)
    provider.add_custom_attributes(ca)
    try:
        provider.add_custom_attributes(ca)
    except APIException:
        pytest.fail('You tried to add a custom attribute that already exists'
                    '({}) and didn\'t get an error!'
                    .format(ca.value))
    finally:
        provider.delete_custom_attributes(ca)


def test_very_long_name_with_special_characters(request, provider):
    """
    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    ca = CustomAttribute(get_random_string(1000), 'very_long_name', None)
    request.addfinalizer(lambda: provider.delete_custom_attributes(ca))
    provider.add_custom_attributes(ca)
    view = navigate_to(provider, 'Details', force=True)
    assert ca.name in view.entities.summary('Custom Attributes').fields


# BZ 540647 was closed as no fix. Code was added that strips underscores from attribute names.
def test_very_long_value_with_special_characters(request, provider):
    """
    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    ca = CustomAttribute('very long value', get_random_string(1000), None)
    request.addfinalizer(lambda: provider.delete_custom_attributes(ca))
    provider.add_custom_attributes(ca)
    view = navigate_to(provider, 'Details', force=True)
    assert ca.value == view.entities.summary('Custom Attributes').get_text_of(ca.name)
