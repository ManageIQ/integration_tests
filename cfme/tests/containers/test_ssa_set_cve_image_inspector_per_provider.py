import random
from collections import namedtuple

import dateparser
import pytest

from cfme import test_requirements
from cfme.common.provider_views import ContainerProvidersView
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

TESTED_ATTRIBUTES_OPENSCAP = (
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
    # add filter for select only active(not archived) images from redHat registry
    filter_image_collection = collection.filter({'active': True, 'redhat_registry': True})
    return random.sample(filter_image_collection.all(), 1).pop()


@pytest.fixture(scope='function')
def openscap_assigned_rand_image(provider, random_image_instance):
    """Returns random Container image that have assigned OpenSCAP policy from image view.
    teardown remove this assignment from image view.
    """
    # assign OpenSCAP policy from chosen Image
    random_image_instance.assign_policy_profiles('OpenSCAP profile')
    yield random_image_instance
    # teardown unassign OpenSCAP policy from chosen Image
    random_image_instance.unassign_policy_profiles('OpenSCAP profile')


@pytest.fixture(scope='function')
def set_cve_location(appliance, provider, soft_assert):
    """Set cve location with cve_url on provider setup
    teardown remove this cve_url from provider setting.
    """
    # update provider settings advance
    provider_edit_view = navigate_to(provider, 'Edit')
    if provider_edit_view.advanced.cve_loc.fill('https://www.redhat.com/security/data/metrics/ds'):
        try:
            provider_edit_view.save.click()
            view = appliance.browser.create_view(ContainerProvidersView)
            view.flash.assert_success_message(
                'Containers Provider "{}" was saved'.format(provider.name))
        except AssertionError:
            soft_assert(False, "{} wasn't added successfully".format(provider.name))
    else:
        provider_edit_view.cancel.click()
    yield
    # teardown unset cve location url
    provider_edit_view = navigate_to(provider, 'Edit')
    if provider_edit_view.advanced.cve_loc.fill(''):
        provider_edit_view.save.click()
    else:
        provider_edit_view.cancel.click()


@pytest.fixture(scope='function')
def set_image_inspector_registry(appliance, provider, soft_assert):
    """Set image inspector registry with url on provider setup
    teardown remove this url from provider setting.
    """
    # update provider settings advance
    provider_edit_view = navigate_to(provider, 'Edit')
    if provider_edit_view.advanced.image_reg.fill('registry.access.redhat.com'):
        try:
            provider_edit_view.save.click()
            view = appliance.browser.create_view(ContainerProvidersView)
            view.flash.assert_success_message(
                'Containers Provider "{}" was saved'.format(provider.name))
        except AssertionError:
            soft_assert(False, "{} wasn't added successfully".format(provider.name))
    else:
        provider_edit_view.cancel.click()
    yield
    # teardown unset image inspector registry url
    provider_edit_view = navigate_to(provider, 'Edit')
    if provider_edit_view.advanced.cve_loc.fill(''):
        provider_edit_view.save.click()
    else:
        provider_edit_view.cancel.click()


def get_table_attr(instance, table_name, attr):
    # Trying to read the table <table_name> attribute <attr>
    view = navigate_to(instance, 'Details', force=True)
    table = getattr(view.entities, table_name, None)
    if table:
        return table.read().get(attr)


def verify_ssa_image_attributes(provider, soft_assert, rand_image):
    """After SSA run finished, go over Image Summary tables attributes that related to OpenSCAP
    And verify SSA pass as expected
    """
    view = navigate_to(rand_image, 'Details')
    for tbl, attr, verifier in TESTED_ATTRIBUTES_OPENSCAP:

        table = getattr(view.entities, tbl)
        table_data = {k.lower(): v for k, v in table.read().items()}

        if not soft_assert(attr.lower() in table_data, '{} table has missing attribute \'{}\''
                .format(tbl, attr)):
            continue
        provider.refresh_provider_relationships()
        wait_for_retval = wait_for(
            get_table_attr,
            func_args=[rand_image, tbl, attr],
            message='Trying to get attribute "{}" of table "{}"'.format(attr, tbl),
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


def test_cve_location_update_value(provider, soft_assert, delete_all_container_tasks,
                                   set_cve_location, openscap_assigned_rand_image):
    """This test checks RFE BZ 1459189, Allow to specify per Provider the location of
     OpenSCAP CVEs.
     In order to verify the above setup, run a smart state analysis on container image.

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    # Perform SSA Scan then check compliance with last know configuration
    openscap_assigned_rand_image.perform_smartstate_analysis(wait_for_finish=True, timeout='20M')

    # verify image table SSA attributes
    verify_ssa_image_attributes(provider, soft_assert, openscap_assigned_rand_image)


def test_image_inspector_registry_update_value(provider, soft_assert, delete_all_container_tasks,
                                               set_image_inspector_registry,
                                               openscap_assigned_rand_image):
    """This test checks RFE BZ 1459189, Allow to specify per Provider
     The image inspector registry url.
     In order to verify the above setup, run a smart state analysis on container image.

    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    # Perform SSA Scan then check compliance with last know configuration
    openscap_assigned_rand_image.perform_smartstate_analysis(wait_for_finish=True, timeout='20M')

    # verify image table SSA attributes
    verify_ssa_image_attributes(provider, soft_assert, openscap_assigned_rand_image)
