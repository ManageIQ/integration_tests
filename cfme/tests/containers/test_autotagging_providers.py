from collections import namedtuple
import fauxfactory
import pytest
from random import choice
from traceback import format_exc

from cfme.configure.configuration.region_settings import MapTags
from cfme.containers.provider import ContainersProvider
from cfme.containers.node import Node
from cfme.containers.replicator import Replicator
from cfme.containers.image import Image
from cfme.containers.pod import Pod
from cfme.containers.project import Project
from cfme.containers.route import Route

from utils import testgen
from utils.version import current_version
from utils.wait import wait_for
from utils.log import logger


pytestmark = [
    pytest.mark.uncollectif(lambda: current_version() < "5.8"),
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='module')

TEST_OBJECTS = (Pod, Route, Node, Replicator, Project)

values = ['{}{}'.format('value_', fauxfactory.gen_alpha(5).lower()),
          '{}{}'.format('value_', fauxfactory.gen_alphanumeric(5).lower()),
          '{}{}{}'.format('value_', fauxfactory.gen_alpha(3).lower(),
                          fauxfactory.gen_alphanumeric(3))]


def check_smart_management_in_ui(instance, expected_value):
    return instance.summary.smart_management.my_company_tags[0].value == str(expected_value)


def set_label(test_obj, instance, label_name, value):
    try:
        status_code, json_content = test_obj.set_label(instance, label_name, value)
        # temp debugging, remove later
        print('setting label status code is: ' + str(status_code))
    except:
        status_code, json_content = None, format_exc()
    return status_code, json_content


def remove_labels(data_collection):
    for instance, company_tag, set_value, category, results_status, \
            results_message, label_name in data_collection:
                try:
                    instance.remove_label(label_name)
                except:
                    logger.warning('Cannot remove label ({} = {}) for {} {}. '
                                   '(failed to add it previously)'
                                   .format(label_name, set_value,
                                           instance.__class__.__name__, instance.name))


def add_tag(instance, label_name, category):
    mt = MapTags(entity=instance.__class__.__name__,
                 label=label_name, category=category)
    mt.create()


def delete_tag(instance, label_name, category):
    mt = MapTags(entity=instance.__class__.__name__, label=label_name, category=category)
    mt.delete()


def verify_ui(soft_assert, data_collection):
    for instance, company_tag, set_value, category, \
            results_status, results_message, label_name in data_collection:
        if soft_assert(results_status, results_message):
            soft_assert(
                wait_for(
                    lambda: check_smart_management_in_ui(instance, company_tag),
                    num_sec=720, delay=20,
                    fail_func=instance.summary.reload,
                    message='Verifying company tag ({}) for {} exists'
                            .format(company_tag,
                                    instance.__class__.__name__, instance.name),
                    silent_failure=True),
                'Could not find company tag ({} for {} {} in UI.'.format
                (company_tag, instance.__class__.__name__, instance.name)
            )


def add_1_label(provider, appliance, value, label_name=None):
    # Creating random instance for each object in TEST_OBJECTS and create a random label for it.
    label_data = namedtuple('label_data', ['instance', 'company_tag',
                                           'set_value', 'category', 'result_status',
                                           'result_message', 'label_name'])
    data_collection = []
    # Collected data in the form:
    #                <instance>, <company_tag>, <results_status>
    # Adding company tags to each object:
    for test_obj in TEST_OBJECTS:
        if not label_name:
            label_name = '{}{}'.format('label_', fauxfactory.gen_alpha(5))
        get_random_kwargs = {'count': 1, 'appliance': appliance}
        if test_obj is Image:
            get_random_kwargs['ocp_only'] = True
        instance = test_obj.get_random_instances(provider, **get_random_kwargs).pop()
        set_value = '{}{}{}'.format(test_obj.__name__, '_', value)
        category = '{}{}{}'.format('category', '_', fauxfactory.gen_alpha(5))
        company_tag = category + ': ' + set_value
        result_status, result_message = set_label(test_obj, instance, label_name, set_value)
        data_collection.append(
            label_data(instance, company_tag, set_value, category,
                       result_status, result_message, label_name)
        )
    return data_collection


def add_2_labels_same_key_same_value(provider, appliance, value):
    label_data = namedtuple('label_data', ['instance', 'company_tag',
                                           'set_value', 'category', 'result_status',
                                           'result_message', 'label_name'])
    data_collection1, data_collection2 = [], []
    base_category = '{}{}{}'.format('category', '_', fauxfactory.gen_alpha(5))
    label_name = '{}{}'.format('label_', fauxfactory.gen_alpha(5))
    for test_obj in TEST_OBJECTS:
        get_random_kwargs = {'count': 1, 'appliance': appliance}
        if test_obj is Image:
            get_random_kwargs['ocp_only'] = True
        instance, instance2 = test_obj.get_random_instances(provider, count=2)
        category = '{}{}{}'.format(base_category, '_', test_obj.__name__)
        company_tag = '{}{} {}'.format(category, ':', value)
        result_status1, result_message1 = set_label(test_obj, instance, label_name, value)
        # Setting label for same label name and values on a different instance
        result_status2, result_message2 = set_label(test_obj, instance2, label_name, value)
        data_collection1.append(
            label_data(instance, company_tag, value, category, result_status1,
                       result_message1, label_name))
        data_collection2.append(
            label_data(instance, company_tag, value, category, result_status2,
                       result_message2, label_name))
    return data_collection1, data_collection2


@pytest.mark.polarion('CMP-10676')  # 10677, 10680, 10683, 10684
def test_autotagging_1_value(provider, soft_assert, appliance):
    """
    This test:
    1. Creates a label with a key and a value on
        different objects of the same kind (Pod, Project etc..)
    2. Maps a label to the same named category
    3. Verifies under each object that the category was mapped correctly to the label
    """
    # Creating random instance for each object in TEST_OBJECTS and create a random label for it.
    for value in values:
        data_collection = add_1_label(provider, appliance, value=value)
        # Add tag for every selected object
        for instance, company_tag, set_value, category, results_status,\
                results_message, label_name in data_collection:
                    add_tag(instance, label_name, category)
        provider.refresh_provider_relationships()
        # Verify autotagged labels in GUI
        verify_ui(soft_assert, data_collection)
        # Labels deletion from Provider
        remove_labels(data_collection)
        # Labels deletion from GUI
        for instance, company_tag, set_value, category, \
                results_status, results_message, label_name in data_collection:
                    delete_tag(instance, label_name, category)


@pytest.mark.polarion('CMP-10689')
def test_2_objects_same_key_same_value(provider, soft_assert, appliance):
    """
    This test:
    1. Creates 2 labels with identical keys and values on 2
        different objects of the same kind (Pod, Project etc..)
    2. Maps a label to the same named category
    3. Verifies under each object that the category was mapped correctly to the label
    """
    # Creating random instance for each object in TEST_OBJECTS and create a random label for it.
    value = '{}{}'.format('value_', fauxfactory.gen_alpha(5).lower())
    double_data_collection = add_2_labels_same_key_same_value(provider, appliance, value)
    # Because both data collections have identical tags and values,
    # only 1 is selected to be sent to add_tag function.
    data_collection = choice(double_data_collection)
    for instance, company_tag, set_value, category, results_status,\
            results_message, label_name in data_collection:
                add_tag(instance, label_name, category)
    provider.refresh_provider_relationships()
    # Each data collection is checked in the GUI
    for data_collection in double_data_collection:
        verify_ui(soft_assert, data_collection)
    # Labels deletion from Provider
    remove_labels(data_collection)
    # Labels deletion from GUI
    for instance, company_tag, set_value, category, results_status, \
            results_message, label_name in data_collection:
                delete_tag(instance, label_name, category)
