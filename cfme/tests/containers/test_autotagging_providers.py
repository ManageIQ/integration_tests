from traceback import format_exc
from collections import namedtuple

import pytest
import fauxfactory
from cfme.configure.configuration.region_settings import MapTags
from cfme.containers.provider import ContainersProvider
from cfme.containers.node import Node
from cfme.containers.replicator import Replicator
from cfme.containers.image import Image
from cfme.containers.pod import Pod
from cfme.containers.project import Project
from cfme.containers.route import Route
from cfme.exceptions import SetLabelException
from cfme.exceptions import RemoveLabelException

from utils import testgen
from utils.version import current_version
from utils.wait import wait_for


pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='module')

TEST_OBJECTS = (Pod, Route, Node, Replicator, Project)


VALUES_TUPLE = ('value_' + fauxfactory.gen_alpha(5).lower(),
                'value_' + fauxfactory.gen_alphanumeric(5),
                'value_' + fauxfactory.gen_alpha(3).lower() + fauxfactory.gen_alphanumeric(3))


SPECIAL_KEYS = (fauxfactory.gen_alpha(3).lower() + '_' + fauxfactory.gen_alpha(2).lower(),
                fauxfactory.gen_alpha(3).lower() + '.' + fauxfactory.gen_alpha(2).lower())

SPECIAL_VALUES = (fauxfactory.gen_alpha(3).lower() + '_' + fauxfactory.gen_alpha(2).lower(),
                  fauxfactory.gen_alpha(3).lower() + '.' + fauxfactory.gen_alpha(2).lower())


def generate_values():
    values = []
    for value in VALUES_TUPLE:
        value_string = value
        values.append(value_string)
    return values


def check_smart_management_in_ui(instance, expected_value):
    if hasattr(instance.summary, 'smart_management'):
        if instance.summary.smart_management.my_company_tags[0].value == str(expected_value):
            return True
    return False


def set_label(test_obj, instance, name, value):
    try:
        results = test_obj.set_label(instance, name, value)
        return results.success, str(results)
    except SetLabelException:
        return False, format_exc()


def remove_label(test_obj, name, value):
    try:
        results = test_obj.remove_label(test_obj._cli_resource_type, name, value)
        return results.success, str(results)
    except RemoveLabelException:
        return False, format_exc()


def verify_ui(soft_assert, data_collection):
    for instance, company_tag, set_value, results_status, results_message, label_name in data_collection:
        if soft_assert(results_status, results_message):
            soft_assert(
                wait_for(
                    lambda: check_smart_management_in_ui(instance, company_tag),
                    num_sec=120, delay=10,
                    fail_func=instance.summary.reload,
                    message='Verifying company tag ({}) for {} exists'
                        .format(company_tag,
                                instance.__class__.__name__, instance.name),
                    silent_failure=True),
                'Could not find company tag ({} for {} {} in UI.'
                    .format(company_tag, instance.__class__.__name__, instance.name)
            )


def add_1_label(provider, appliance, value, name=None, random_name=False):
    # Creating random instance for each object in TEST_OBJECTS and create a random label for it.
    label_data = namedtuple('label_data', ['instance', 'company_tag', 'set_value', 'result_status',
                                           'result_message', 'label_name'])
    data_collection = []
    # if not name:
    #     name = 'abc' + "_" + fauxfactory.gen_alpha(5)
    # Collected data in the form:
    #                <instance>, <company_tag>, <results_status>
    # Adding company tags to each object:
    for test_obj in TEST_OBJECTS:
        if random_name:
            name = name
        if not random_name:
            name = 'abc' + "_" + fauxfactory.gen_alpha(5)
        get_random_kwargs = {'count': 1, 'appliance': appliance}
        if test_obj is Image:
            get_random_kwargs['ocp_only'] = True
        instance = test_obj.get_random_instances(provider, **get_random_kwargs).pop()
        set_value = test_obj.__name__ + "_" + value
        company_tag = 'category: ' + set_value
        print('the name is: ' + name + " and the value is: " + set_value + " the name is: " + instance.name)
        result_status, result_message = set_label(test_obj, instance, name, set_value)
        data_collection.append(
            label_data(instance, company_tag, set_value, result_status, result_message, name)
        )
    return data_collection


def add_2_labels_same_value(provider, appliance, value):
    # Creating random instance for each object in TEST_OBJECTS and create a random label for it.
    label_data = namedtuple('label_data', ['instance', 'company_tag', 'result_status',
                                           'result_message', 'label_name'])
    data_collection = []
    data_collection2 = []
    name = 'abc' + "_" + fauxfactory.gen_alpha(5)
    # Collected data in the form:
    #                <instance>, <company_tag>, <results_status>
    # Adding company tags to each object:
    for test_obj in TEST_OBJECTS:
        get_random_kwargs = {'count': 1, 'appliance': appliance}
        if test_obj is Image:
            get_random_kwargs['ocp_only'] = True
        instance = test_obj.get_random_instances(provider, **get_random_kwargs).pop()
        company_tag1 = 'category: ' + value
        company_tag2 = 'category: ' + value
        result_status1, result_message1 = set_label(test_obj, instance, name, value)
        instance2 = test_obj.get_random_instances(provider, **get_random_kwargs).pop()
        while instance2 == instance:
            instance2 = test_obj.get_random_instances(provider, **get_random_kwargs).pop()
        result_status2, result_message2 = set_label(test_obj, instance2, name, value)
        data_collection.append(
            label_data(instance, company_tag1, result_status1, result_message1, name))
        data_collection2.append(
            label_data(instance, company_tag2, result_status2, result_message2, name))
    return data_collection, data_collection2


def add_2_labels_same_key(provider, appliance, value1, value2):
    # Creating random instance for each object in TEST_OBJECTS and create a random label for it.
    label_data = namedtuple('label_data', ['instance', 'company_tag', 'result_status',
                                           'result_message', 'label_name'])
    data_collection = []
    data_collection2 = []
    name = 'abc' + "_" + fauxfactory.gen_alpha(5)
    # Collected data in the form:
    #                <instance>, <company_tag>, <results_status>
    # Adding company tags to each object:
    for test_obj in TEST_OBJECTS:
        get_random_kwargs = {'count': 1, 'appliance': appliance}
        if test_obj is Image:
            get_random_kwargs['ocp_only'] = True
        instance = test_obj.get_random_instances(provider, **get_random_kwargs).pop()
        company_tag1 = 'category: ' + value1
        company_tag2 = 'category: ' + value2
        result_status1, result_message1 = set_label(test_obj, instance, name, value1)
        instance2 = test_obj.get_random_instances(provider, **get_random_kwargs).pop()
        while instance2 == instance:
            instance2 = test_obj.get_random_instances(provider, **get_random_kwargs).pop()
        result_status2, result_message2 = set_label(test_obj, instance2, name, value2)
        data_collection.append(
            label_data(instance, company_tag1, result_status1, result_message1, name))
        data_collection2.append(
            label_data(instance2, company_tag2, result_status2, result_message2, name))
    return data_collection, data_collection2


@pytest.mark.polarion('CMP-10676') # 10677, 10680
def test_autotagging_1_value(provider, soft_assert, appliance):
    values_bundle = generate_values()
    for value in values_bundle:
        data_collection = add_1_label(provider, appliance, value=value)
        for instance, company_tag, set_value, results_status, results_message, label_name in data_collection:
            print(instance)
            mt = MapTags(entity=instance.__class__.__name__, label=label_name, category=set_value)
            mt.create()
        provider.refresh_provider_relationships()
        verify_ui(soft_assert, data_collection)
        # Labels deletion
        for instance, company_tag, results_status, results_message, label_name in data_collection:
            remove_label(instance, instance.name, label_name)


@pytest.mark.polarion('CMP-10680')
def test_2_objects_same_key_same_value(provider, soft_assert, appliance):
    value = 'value_' + fauxfactory.gen_alpha(5).lower()
    double_data_collection = add_2_labels_same_value(provider, appliance, value)
    for data_collection in double_data_collection:
        # Set the tag and category here in Map Tags
        provider.refresh_provider_relationships()
        # Verify that the labels appear in the UI:
        verify_ui(soft_assert, data_collection)
        # Find a way to reload an instance
    # Labels deletion
    for data_collection in double_data_collection:
        for instance, company_tag, results_status, results_message, label_name in data_collection:
            remove_label(instance, instance.name, label_name)


@pytest.mark.polarion('CMP-10682')
def test_2_objects_same_key(provider, soft_assert, appliance):
    value1 = 'value_' + fauxfactory.gen_alpha(5).lower()
    value2 = 'value_' + fauxfactory.gen_alpha(5).lower()
    double_data_collection = add_2_labels_same_key(provider, appliance, value1, value2)
    # You can't add the same key twice in the Map Tags screen.
    # The second label setting just overwrite the first with a new value. This test is highly questionable
    # Should it just verify that only the second company tag actually appears
    # Verify 2 different values appear in My Company Tags
    data_collection1, data_collection2 = double_data_collection
    # Set the tag and category here in Map Tags
    provider.refresh_provider_relationships()
    # Verify that the labels appear in the UI:
    verify_ui(soft_assert, data_collection2)
    # Labels deletion
    for data_collection in double_data_collection:
        for instance, company_tag, results_status, results_message, label_name in data_collection:
            remove_label(instance, instance.name, label_name)


@pytest.mark.polarion('CMP-10683')
def test_special_chars_key(provider, soft_assert, appliance):
    value = 'value_' + fauxfactory.gen_alpha(5).lower()
    for name in SPECIAL_KEYS:
        data_collection = add_1_label(provider, appliance, value, name)
        # Set the tag and category here in Map Tags
        # Set the tag and category here in Map Tags
        provider.refresh_provider_relationships()
        # Verify that the labels appear in the UI:
        verify_ui(soft_assert, data_collection)
        # Labels deletion
        for instance, company_tag, results_status, results_message, label_name in data_collection:
            remove_label(instance, instance.name, label_name)


@pytest.mark.polarion('CMP-10684')
def test_special_chars_key(provider, soft_assert, appliance):
    name = 'abc_' + fauxfactory.gen_alpha(5).lower()
    for value in SPECIAL_VALUES:
        data_collection = add_1_label(provider, appliance, value, name)
        # Set the tag and category here in Map Tags
        provider.refresh_provider_relationships()
        # Verify that the labels appear in the UI:
        verify_ui(soft_assert, data_collection)
        # Labels deletion
        for instance, company_tag, results_status, results_message, label_name in data_collection:
            remove_label(instance, instance.name, label_name)
