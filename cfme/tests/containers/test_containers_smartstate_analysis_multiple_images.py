import dateparser
import pytest
import random

from collections import namedtuple
from cfme.containers.image import Image
from cfme.containers.provider import (ContainersProvider, ContainersTestItem,
                                      refresh_and_navigate)
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.meta(server_roles='+smartproxy'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')]


AttributeToVerify = namedtuple('AttributeToVerify', ['table', 'attr', 'verifier'])

TESTED_ATTRIBUTES__openscap_off = (
    AttributeToVerify('configuration', 'OpenSCAP Results', bool),
    AttributeToVerify('configuration', 'OpenSCAP HTML', lambda val: val == 'Available'),
    AttributeToVerify('configuration', 'Last scan', dateparser.parse)
)
TESTED_ATTRIBUTES__openscap_on = TESTED_ATTRIBUTES__openscap_off + (
    AttributeToVerify('compliance', 'Status', lambda val: val.lower() != 'never verified'),
    AttributeToVerify('compliance', 'History', lambda val: val == 'Available')
)

TEST_ITEMS = (
    pytest.mark.polarion('CMP-9497')(
        ContainersTestItem(Image, 'CMP-9497',
                           is_openscap=False,
                           tested_attr=TESTED_ATTRIBUTES__openscap_off)
    ),
    pytest.mark.polarion('CMP-10065')(
        ContainersTestItem(Image, 'CMP-10065',
                           is_openscap=True,
                           tested_attr=TESTED_ATTRIBUTES__openscap_on)
    )
)

TASKS_RUN_PARALLEL = 3
TASK_TIMEOUT = 20
NUM_SELECTED_IMAGES = 4


@pytest.fixture(scope='function')
def delete_all_container_tasks(appliance):
    col = appliance.collections.tasks.filter({'tab': 'AllTasks'})
    col.delete_all()


@pytest.fixture(scope='function')
def random_image_instances(appliance):
    collection = appliance.collections.container_images
    # add filter for select only active(not archived) images from redHat registry
    filter_image_collection = collection.filter({'active': True, 'redhat_registry': True})
    return random.sample(filter_image_collection.all(), NUM_SELECTED_IMAGES)


@pytest.mark.polarion('10031')
def test_check_compliance(provider, random_image_instances, appliance):

    collection = appliance.collections.container_images
    # create conditions list that will match the images that we want to check
    conditions = []
    for image_instance in random_image_instances:
        conditions.append({'id': image_instance.id})
    # assign OpenSCAP policy
    collection.assign_policy_profiles_multiple_entities(random_image_instances, conditions,
                                                        'OpenSCAP profile')

    # Verify Image summary
    collection.check_compliance_multiple_images(random_image_instances)


def get_table_attr(instance, table_name, attr):
    # Trying to read the table <table_name> attribute <attr>
    view = refresh_and_navigate(instance, 'Details')
    table = getattr(view.entities, table_name, None)
    if table:
        return table.read().get(attr)


@pytest.mark.parametrize(('test_item'), TEST_ITEMS)
def test_containers_smartstate_analysis(provider, test_item,
                                        delete_all_container_tasks, soft_assert,
                                        random_image_instances, appliance):

    collection = appliance.collections.container_images
    # create conditions list that will match the images that we want to check
    conditions = []
    for image_instance in random_image_instances:
        conditions.append({'id': image_instance.id})
    # assign OpenSCAP policy
    if test_item.is_openscap:
        collection.assign_policy_profiles_multiple_entities(random_image_instances, conditions,
                                                           'OpenSCAP profile')
    else:
        collection.unassign_policy_profiles_multiple_entities(random_image_instances, conditions,
                                                            'OpenSCAP profile')

    # perform smartstate analysis
    # 3 tasks are running in parallel , each task has 20M timeout threshold definition
    timeout = "{timeout}M".format(timeout=NUM_SELECTED_IMAGES / TASKS_RUN_PARALLEL * TASK_TIMEOUT if
                                  NUM_SELECTED_IMAGES % TASKS_RUN_PARALLEL == 0 else
                                  NUM_SELECTED_IMAGES / TASKS_RUN_PARALLEL * TASK_TIMEOUT +
                                  TASK_TIMEOUT)
    assert collection.perform_smartstate_analysis_multiple_images(
        random_image_instances, wait_for_finish=True, timeout=timeout), (
        'Some Images SSA tasks finished with error message,'
        ' see logger for more details.')

    # Verify Image summary
    for image_instance in random_image_instances:
        view = navigate_to(image_instance, 'Details')
        for tbl, attr, verifier in test_item.tested_attr:

            table = getattr(view.entities, tbl)
            table_data = {k.lower(): v for k, v in table.read().items()}

            if not soft_assert(attr.lower() in table_data,
                               '{} table has missing attribute \'{}\''.format(tbl, attr)):
                continue
            provider.refresh_provider_relationships()
            wait_for_retval = wait_for(lambda: get_table_attr(image_instance, tbl, attr),
                                       message='Trying to get attribute "{}" of table "{}"'.format(
                                           attr, tbl),
                                       delay=5, num_sec=120, silent_failure=True)
            if not wait_for_retval:
                soft_assert(False, 'Could not get attribute "{}" for "{}" table.'
                            .format(attr, tbl))
                continue
            value = wait_for_retval.out
            soft_assert(verifier(value),
                        '{}.{} attribute has unexpected value ({})'.format(tbl, attr, value))
