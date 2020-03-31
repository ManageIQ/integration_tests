import random
from collections import namedtuple

import dateparser
import pytest

from cfme import test_requirements
from cfme.containers.image import Image
from cfme.containers.provider import ContainersProvider
from cfme.containers.provider import ContainersTestItem
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.meta(server_roles='+smartproxy'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function'),
    test_requirements.containers
]

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
    ContainersTestItem(Image, 'openscap_off', is_openscap=False,
                       tested_attr=TESTED_ATTRIBUTES__openscap_off),
    ContainersTestItem(Image, 'openscap_on', is_openscap=True,
                       tested_attr=TESTED_ATTRIBUTES__openscap_on)
)

NUM_SELECTED_IMAGES = 1


@pytest.fixture(scope='function')
def delete_all_container_tasks(appliance):
    col = appliance.collections.tasks.filter({'tab': 'AllTasks'})
    col.delete_all()


@pytest.fixture(scope='function')
def random_image_instance(appliance):
    collection = appliance.collections.container_images
    # add filter for select only active(not archived) images from redHat registry
    filter_image_collection = collection.filter({'active': True, 'redhat_registry': True})
    return random.sample(filter_image_collection.all(), NUM_SELECTED_IMAGES).pop()


@pytest.mark.polarion('10030')
def test_manage_policies_navigation(random_image_instance):
    """
    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    random_image_instance.assign_policy_profiles('OpenSCAP profile')


@pytest.mark.polarion('10031')
def test_check_compliance(random_image_instance):
    """
    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    random_image_instance.assign_policy_profiles('OpenSCAP profile')
    random_image_instance.check_compliance()


def get_table_attr(instance, table_name, attr):
    # Trying to read the table <table_name> attribute <attr>
    view = navigate_to(instance, 'Details', force=True)
    table = getattr(view.entities, table_name, None)
    if table:
        return table.read().get(attr)


@pytest.mark.parametrize(('test_item'), TEST_ITEMS)
def test_containers_smartstate_analysis(provider, test_item, soft_assert,
                                        delete_all_container_tasks,
                                        random_image_instance):

    """
    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    if test_item.is_openscap:
        random_image_instance.assign_policy_profiles('OpenSCAP profile')
    else:
        random_image_instance.unassign_policy_profiles('OpenSCAP profile')

    random_image_instance.perform_smartstate_analysis(wait_for_finish=True)

    view = navigate_to(random_image_instance, 'Details')
    for tbl, attr, verifier in test_item.tested_attr:

        table = getattr(view.entities, tbl)
        table_data = {k.lower(): v for k, v in table.read().items()}

        if not soft_assert(attr.lower() in table_data,
                f'{tbl} table has missing attribute \'{attr}\''):
            continue
        provider.refresh_provider_relationships()
        wait_for_retval = wait_for(lambda: get_table_attr(random_image_instance, tbl, attr),
                                   message='Trying to get attribute "{}" of table "{}"'.format(
                                       attr, tbl),
                                   delay=5, num_sec=120, silent_failure=True)
        if not wait_for_retval:
            soft_assert(False, 'Could not get attribute "{}" for "{}" table.'
                        .format(attr, tbl))
            continue
        value = wait_for_retval.out
        soft_assert(verifier(value),
            f'{tbl}.{attr} attribute has unexpected value ({value})')


@pytest.mark.parametrize(('test_item'), TEST_ITEMS)
def test_containers_smartstate_analysis_api(provider, test_item, soft_assert,
                                        delete_all_container_tasks, random_image_instance):
    """
       Test initiating a SmartState Analysis scan via the CFME API through the ManageIQ API Client
       entity class.

       RFE: BZ 1486362

    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """

    if test_item.is_openscap:
        random_image_instance.assign_policy_profiles('OpenSCAP profile')
    else:
        random_image_instance.unassign_policy_profiles('OpenSCAP profile')

    original_scan = random_image_instance.last_scan_attempt_on

    random_image_instance.scan()

    task = provider.appliance.collections.tasks.instantiate(
        name=f"Container Image Analysis: '{random_image_instance.name}'", tab='AllTasks')

    task.wait_for_finished()

    soft_assert(original_scan != random_image_instance.last_scan_attempt_on,
                'SmartState Anaysis scan has failed')
