import random
from traceback import format_exc
from collections import namedtuple

import pytest
import fauxfactory

from cfme.containers.provider import ContainersProvider
from cfme.containers.pod import Pod
from cfme.containers.service import Service
from cfme.containers.node import Node
from cfme.containers.replicator import Replicator
from cfme.containers.image import Image
from cfme.containers.project import Project
from cfme.containers.route import Route
from cfme.containers.template import Template
from cfme.exceptions import SetLabelException

from utils import testgen
from utils.wait import wait_for
from utils.log import logger
from utils.blockers import BZ


pytestmark = [
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='module')


TEST_OBJECTS = (Pod, Service, Route, Template, Node, Replicator, Image, Project)


def check_labels_in_ui(instance, name, expected_value):
    if hasattr(instance.summary, 'labels') and \
            hasattr(instance.summary.labels, name.lower()):
        return getattr(instance.summary.labels, name.lower()).text_value == str(expected_value)
    return False


@pytest.fixture(scope='module')
def random_labels(provider, appliance):
    # Creating random instance for each object in TEST_OBJECTS and create a random label for it.
    label_data = namedtuple('label_data', ['instance', 'label_name', 'label_value',
                                           'result_status', 'result_message'])
    data_collection = []  # Collected data in the form:
    #                <instance>, <label_name>, <label_value>, <results_status>
    # Adding label to each object:
    for test_obj in TEST_OBJECTS:
        get_random_kwargs = {'count': 1, 'appliance': appliance}
        if test_obj is Image:
            get_random_kwargs['ocp_only'] = True
        instance = test_obj.get_random_instances(provider, **get_random_kwargs).pop()
        name = fauxfactory.gen_alpha(1) + fauxfactory.gen_alphanumeric(random.randrange(1, 62))
        value = fauxfactory.gen_alphanumeric(random.randrange(1, 63))
        try:
            results = test_obj.set_label(instance, name, value)
            result_status, result_message = results.success, str(results)
        except SetLabelException:
            result_status, result_message = False, format_exc()

        data_collection.append(
            label_data(instance, name, value, result_status, result_message)
        )
    return data_collection


@pytest.mark.polarion('CMP-10572')
def test_labels_create(provider, soft_assert, random_labels):

    provider.refresh_provider_relationships()
    # Verify that the labels appear in the UI:
    for instance, label_name, label_value, results_status, results_message in random_labels:
        if soft_assert(results_status, results_message):
            soft_assert(
                wait_for(
                    lambda: check_labels_in_ui(instance, label_name, label_value),
                    num_sec=120, delay=10,
                    fail_func=instance.summary.reload,
                    message='Verifying label ({} = {}) for {} {} exists'
                            .format(label_name, label_value,
                                    instance.__class__.__name__, instance.name),
                    silent_failure=True),
                'Could not find label ({} = {}) for {} {} in UI.'
                .format(label_name, label_value, instance.__class__.__name__, instance.name)
            )


@pytest.mark.meta(blockers=[BZ(1451832, forced_streams=['5.7', '5.8', 'upstream'])])
@pytest.mark.polarion('CMP-10572')
def test_labels_remove(provider, soft_assert, random_labels):
    # Removing the labels
    for instance, label_name, label_value, results_status, _ in random_labels:
        if results_status:
            instance.remove_label(label_name)
        else:
            logger.warning('Cannot remove label ({} = {}) for {} {}. (failed to add it previously)'
                           .format(label_name, label_value,
                                   instance.__class__.__name__, instance.name))

    provider.refresh_provider_relationships()
    # Verify that the labels removed successfully from UI:
    for instance, label_name, label_value, results_status, _ in random_labels:
        if results_status:
            soft_assert(
                wait_for(
                    lambda: not check_labels_in_ui(instance, label_name, label_value),
                    num_sec=120, delay=10,
                    fail_func=instance.summary.reload,
                    message='Verifying label ({} = {}) for {} {} removed'
                            .format(label_name, label_value,
                                    instance.__class__.__name__, instance.name),
                    silent_failure=True),
                'Label ({} = {}) for {} {} found in UI (but should be removed).'
                .format(label_name, label_value, instance.__class__.__name__, instance.name)
            )
