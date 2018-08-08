# -*- coding: utf-8 -*-
import pytest

from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.wait import wait_for


@pytest.fixture(scope="function")
def new_vm(appliance, provider, request):
    if provider.one_of(CloudProvider):
        vm = appliance.collections.cloud_instances.instantiate(random_vm_name(context='cockpit'),
                                                               provider)
    else:
        vm = appliance.collections.infra_vms.instantiate(random_vm_name(context='cockpit'),
                                                         provider)
    if not provider.mgmt.does_vm_exist(vm.name):
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")
        request.addfinalizer(vm.cleanup_on_provider)
    return vm


@pytest.mark.rhv3
@pytest.mark.uncollectif(
    lambda appliance, provider: appliance.version < "5.9" or provider.one_of(GCEProvider))
@pytest.mark.provider([CloudProvider, InfraProvider])
@pytest.mark.parametrize('enable', [False, True], ids=['disabled', 'enabled'])
def test_cockpit_server_role(appliance, provider, setup_provider, new_vm, enable):
    """ The test checks the cockpit "Web Console" button enable and disabled working.

    Metadata:
        test_flag: inventory
    """

    if enable:
        appliance.server.settings.enable_server_roles('cockpit_ws')
        wait_for(lambda: appliance.server_roles['cockpit_ws'] is True, delay=20, timeout=300)
    if not enable:
        appliance.server.settings.disable_server_roles('cockpit_ws')
        wait_for(lambda: appliance.server_roles['cockpit_ws'] is False, delay=20, timeout=300)

    view = navigate_to(new_vm, 'Details')
    if enable:
        assert view.toolbar.access.item_enabled('Web Console')
        appliance.server.settings.disable_server_roles('cockpit_ws')
    else:
        assert not view.toolbar.access.item_enabled('Web Console')
