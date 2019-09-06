import random
from collections import namedtuple
from traceback import format_exc

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.containers.image import Image
from cfme.containers.image import ImageCollection
from cfme.containers.pod import Pod
from cfme.containers.pod import PodCollection
from cfme.containers.project import Project
from cfme.containers.project import ProjectCollection
from cfme.containers.provider import ContainersProvider
from cfme.containers.replicator import Replicator
from cfme.containers.replicator import ReplicatorCollection
from cfme.containers.route import Route
from cfme.containers.route import RouteCollection
from cfme.containers.service import Service
from cfme.containers.service import ServiceCollection
from cfme.containers.template import Template
from cfme.containers.template import TemplateCollection
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import GH
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='module'),
    test_requirements.containers
]

# TODO Add Node back into the list when other classes are updated to use WT views and widgets.
DataSet = namedtuple('DataSet', ['obj', 'collection_obj'])
TEST_OBJECTS = (
    DataSet(Image, ImageCollection),
    DataSet(Pod, PodCollection),
    DataSet(Service, ServiceCollection),
    DataSet(Route, RouteCollection),
    DataSet(Template, TemplateCollection),
    DataSet(Replicator, ReplicatorCollection),
    DataSet(Project, ProjectCollection)
)


def check_labels_in_ui(instance, name, expected_value):
    view = navigate_to(instance, 'Details', force=True)
    if view.entities.labels.is_displayed:
        try:
            return view.entities.labels.get_text_of(name) == str(expected_value)
        except NameError:
            return False
    return False


@pytest.fixture(scope='module')
def random_labels(provider, appliance):
    # Creating random instance for each object in TEST_OBJECTS and create a random label for it.
    label_data = namedtuple('label_data', ['instance', 'label_name', 'label_value',
                                           'status_code', 'json_content'])
    data_collection = []  # Collected data in the form:
    #                <instance>, <label_name>, <label_value>, <results_status>
    # Adding label to each object:
    for test_obj in TEST_OBJECTS:
        instance = test_obj.collection_obj(appliance).get_random_instances().pop()
        label_key = fauxfactory.gen_alpha(1) + \
            fauxfactory.gen_alphanumeric(random.randrange(1, 62))
        value = fauxfactory.gen_alphanumeric(random.randrange(1, 63))
        try:
            status_code, json_content = instance.set_label(label_key, value)
        except NameError:
            status_code, json_content = None, format_exc()

        data_collection.append(
            label_data(instance, label_key, value, status_code, json_content)
        )
    return data_collection
    # In case that test_labels_remove is skipped we should remove the labels:
    for _, label_key, status_code, _ in data_collection:
        if status_code and label_key in instance.get_labels():
            instance.remove_label(label_key)


@pytest.mark.meta(blockers=[GH('ManageIQ/integration_tests:7687')])
def test_labels_create(provider, soft_assert, random_labels):

    """
    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    provider.refresh_provider_relationships()
    # Verify that the labels appear in the UI:
    for instance, label_name, label_value, status_code, json_content in random_labels:
        if soft_assert(status_code in (200, 201), str(json_content)):
            soft_assert(
                wait_for(
                    lambda: check_labels_in_ui(instance, label_name, label_value),
                    num_sec=180, delay=10,
                    message='Verifying label ({} = {}) for {} {} exists'
                            .format(label_name, label_value,
                                    instance.__class__.__name__, instance.name),
                    silent_failure=True),
                'Could not find label ({} = {}) for {} {} in UI.'
                .format(label_name, label_value, instance.__class__.__name__, instance.name)
            )


@pytest.mark.meta(blockers=[GH('ManageIQ/integration_tests:7687')])
def test_labels_remove(provider, soft_assert, random_labels):
    """
    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    # Removing the labels
    for instance, label_name, label_value, status_code, _ in random_labels:
        if status_code:
            instance.remove_label(label_name)
        else:
            logger.warning('Cannot remove label ({} = {}) for {} {}. (failed to add it previously)'
                           .format(label_name, label_value,
                                   instance.__class__.__name__, instance.name))

    provider.refresh_provider_relationships()
    # Verify that the labels removed successfully from UI:
    for instance, label_name, label_value, status_code, _ in random_labels:
        if status_code:
            soft_assert(
                wait_for(
                    lambda: not check_labels_in_ui(instance, label_name, label_value),
                    num_sec=180, delay=10,
                    message='Verifying label ({} = {}) for {} {} removed'
                            .format(label_name, label_value,
                                    instance.__class__.__name__, instance.name),
                    silent_failure=True),
                'Label ({} = {}) for {} {} found in UI (but should be removed).'
                .format(label_name, label_value, instance.__class__.__name__, instance.name)
            )
