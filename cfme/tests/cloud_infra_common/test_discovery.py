# -*- coding: utf-8 -*-
import time

import pytest

from cfme import test_requirements
from cfme.common.provider import BaseProvider
from cfme.exceptions import CFMEException
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.markers.env_markers.provider import all_required
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError


pytestmark = [
    pytest.mark.tier(2),
    test_requirements.discovery,
]


@pytest.fixture(scope="module")
def vm_name():
    return random_vm_name("dscvry")


@pytest.fixture(scope="module")
def vm_crud(vm_name, provider):
    collection = provider.appliance.provider_based_collection(provider)
    return collection.instantiate(vm_name, provider)


def if_scvmm_refresh_provider(provider):
    # No eventing from SCVMM so force a relationship refresh
    if isinstance(provider, SCVMMProvider):
        provider.refresh_provider_relationships()


def wait_for_vm_state_changes(vm, timeout=600):

    count = 0
    while count < timeout:
        try:
            vm_state = vm.find_quadicon(from_any_provider=True).data['state'].lower()
            logger.info("Quadicon state for %s is %s", vm.name, repr(vm_state))
            if "archived" in vm_state:
                return True
            elif "orphaned" in vm_state:
                raise CFMEException("VM should be Archived but it is Orphaned now.")
        except Exception as e:
            logger.exception(e)
            pass
        time.sleep(15)
        count += 15
    if count > timeout:
        raise CFMEException("VM should be Archived but it is Orphaned now.")


@pytest.mark.rhv2
@pytest.mark.provider(
    [BaseProvider],
    scope='module',
    required_fields=[['templates', 'small_template']]  # default for create_on_provider
)
def test_vm_discovery(request, setup_provider, provider, vm_crud):
    """ Tests whether cfme will discover a vm change (add/delete) without being manually refreshed.

    Polarion:
        assignee: ghubale
        casecomponent: Infra
        initialEstimate: 1/4h
        tags: power
        setup:
            1. Desired provider set up
        testSteps:
            1. Create a virtual machine on the provider.
            2. Wait for the VM to appear
            3. Delete the VM from the provider (not using CFME)
            4. Wait for the VM to become Archived.
    """

    @request.addfinalizer
    def _cleanup():
        vm_crud.cleanup_on_provider()
        if_scvmm_refresh_provider(provider)

    try:
        vm_crud.create_on_provider(allow_skip="default")
    except KeyError:
        msg = 'Missing template for provider {}'.format(provider.key)
        logger.exception(msg)
        pytest.skip(msg)
    if_scvmm_refresh_provider(provider)

    try:
        vm_crud.wait_to_appear(timeout=600, load_details=False)
    except TimedOutError:
        pytest.fail("VM was not found in CFME")
    vm_crud.cleanup_on_provider()
    if_scvmm_refresh_provider(provider)
    wait_for_vm_state_changes(vm_crud)


def provider_classes(appliance):
    required_providers = all_required(appliance.version)

    selected = dict(infra=[], cloud=[], container=[])
    # we want to collect these provider categories
    for cat in selected.keys():
        selected[cat].extend(
            set(  # quick and dirty uniqueness for types/versions
                prov.klass
                for prov in required_providers
                if prov.category == cat
            )
        )
    return selected


@pytest.mark.tier(0)
def test_provider_type_support(appliance, soft_assert):
    """Test availability of GCE provider in downstream CFME builds

    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1671844

    Polarion:
        assignee: mshriver
        initialEstimate: 1/10h
        casecomponent: WebUI
    """
    classes_to_test = provider_classes(appliance)
    for category, providers in classes_to_test.items():
        try:
            collection = getattr(appliance.collections, providers[0].collection_name)
        except AttributeError:
            msg = 'Missing collection name for a provider class, cannot test UI field'
            logger.exception(msg)
            pytest.fail(msg)
        view = navigate_to(collection, 'Add')
        options = [o.text for o in view.prov_type.all_options]
        for provider_class in providers:
            type_text = provider_class.ems_pretty_name
            if type_text is not None:
                soft_assert(
                    type_text in options,
                    'Provider type [{}] not in Add provider form options [{}]'
                    .format(type_text, options)
                )
