import random
from collections import namedtuple

import dateparser
import pytest

from cfme import test_requirements
from cfme.containers.provider import ContainersProvider
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

TESTED_ATTRIBUTES__openscap = (
    AttributeToVerify('configuration', 'OpenSCAP Results', bool),
    AttributeToVerify('configuration', 'OpenSCAP HTML', lambda val: val == 'Available'),
    AttributeToVerify('configuration', 'Last scan', dateparser.parse),
    AttributeToVerify('compliance', 'Status', lambda val: val.lower() != 'never verified'),
    AttributeToVerify('compliance', 'History', lambda val: val == 'Available')
)


@pytest.fixture(scope='function')
def delete_all_container_tasks(appliance):
    col = appliance.collections.tasks.filter({'tab': 'AllTasks'})
    col.delete_all()


@pytest.fixture(scope='function')
def random_image_instance(appliance):
    collection = appliance.collections.container_images
    return random.sample(collection.all(), 1).pop()


@pytest.fixture(scope='function')
def openscap_assigned_rand_image(provider, random_image_instance):
    """Returns random Container image that have assigned OpenSCAP policy from provider view.
    teardown remove this assignment from provider view.
    """
    # unassign OpenSCAP policy from chosen Image
    random_image_instance.unassign_policy_profiles('OpenSCAP profile')
    # assign policy from provider view
    provider.assign_policy_profiles('OpenSCAP profile')
    yield random_image_instance
    provider.unassign_policy_profiles('OpenSCAP profile')


def get_table_attr(instance, table_name, attr):
    # Trying to read the table <table_name> attribute <attr>
    view = navigate_to(instance, 'Details', force=True)
    table = getattr(view.entities, table_name, None)
    if table:
        return table.read().get(attr)


def test_check_compliance_provider_policy(provider, soft_assert, delete_all_container_tasks,
                                          openscap_assigned_rand_image):

    """
    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    # Perform SSA Scan then check compliance with last know configuration
    openscap_assigned_rand_image.perform_smartstate_analysis(wait_for_finish=True, timeout='20M')

    view = navigate_to(openscap_assigned_rand_image, 'Details')
    for tbl, attr, verifier in TESTED_ATTRIBUTES__openscap:

        table = getattr(view.entities, tbl)
        table_data = {k.lower(): v for k, v in table.read().items()}

        if not soft_assert(attr.lower() in table_data, '{} table has missing attribute \'{}\''
                           .format(tbl, attr)):
            continue
        provider.refresh_provider_relationships()
        wait_for_retval = wait_for(
            get_table_attr,
            func_args=[openscap_assigned_rand_image, tbl, attr],
            message=f'Trying to get attribute "{attr}" of table "{tbl}"',
            delay=5,
            num_sec=120,
            silent_failure=True
        )
        if not wait_for_retval:
            soft_assert(False, 'Could not get attribute "{}" for "{}" table.'
                        .format(attr, tbl))
            continue
        value = wait_for_retval.out
        soft_assert(verifier(value), '{}.{} attribute has unexpected value ({})'
                    .format(tbl, attr, value))
