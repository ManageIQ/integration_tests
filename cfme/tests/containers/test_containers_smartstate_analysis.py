import dateparser
from collections import namedtuple

import pytest

from cfme.containers.image import Image
from cfme.containers.provider import (ContainersProvider, ContainersTestItem,
                                      refresh_and_navigate)

from cfme.utils.wait import wait_for
from cfme.configure.tasks import delete_all_tasks
from cfme.utils.appliance.implementations.ui import navigate_to


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
    pytest.mark.polarion('CMP-9496')(
        ContainersTestItem(Image, 'CMP-9496',
                           is_openscap=False,
                           tested_attr=TESTED_ATTRIBUTES__openscap_off)
    ),
    pytest.mark.polarion('CMP-10064')(
        ContainersTestItem(Image, 'CMP-10064',
                           is_openscap=True,
                           tested_attr=TESTED_ATTRIBUTES__openscap_on)
    )
)


@pytest.fixture(scope='function')
def delete_all_container_tasks():
    delete_all_tasks('AllTasks')


@pytest.fixture(scope='function')
def random_image_instance(provider, appliance):
    return Image.get_random_instances(provider, 1, appliance).pop()


@pytest.mark.polarion('10030')
def test_manage_policies_navigation(random_image_instance):
    random_image_instance.assign_policy_profiles('OpenSCAP profile')


@pytest.mark.polarion('10031')
def test_check_compliance(random_image_instance):
    random_image_instance.assign_policy_profiles('OpenSCAP profile')
    random_image_instance.check_compliance()


def get_table_attr(instance, table_name, attr):
    # Trying to read the table <table_name> attribute <attr>
    view = refresh_and_navigate(instance, 'Details')
    table = getattr(view.entities, table_name, None)
    if table:
        return table.read().get(attr)


@pytest.mark.parametrize(('test_item'), TEST_ITEMS)
def test_containers_smartstate_analysis(provider, test_item, soft_assert,
                                        delete_all_container_tasks,
                                        random_image_instance):

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
                '{} table has missing attribute \'{}\''.format(tbl, attr)):
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
            '{}.{} attribute has unexpected value ({})'.format(tbl, attr, value))
