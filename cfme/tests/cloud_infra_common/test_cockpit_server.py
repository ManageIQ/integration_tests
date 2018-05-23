# -*- coding: utf-8 -*-
import pytest

from cfme.cloud.instance import Instance
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.common.provider import CloudInfraProvider
from cfme.infrastructure.virtual_machines import InfraVm
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.wait import wait_for


@pytest.fixture(scope="function")
def new_vm(provider, request):
    if provider.one_of(CloudProvider):
        vm = Instance.factory(random_vm_name(context='cockpit'), provider)
    else:
        vm = InfraVm.factory(random_vm_name(context='cockpit'), provider)
    if not provider.mgmt.does_vm_exist(vm.name):
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")
        request.addfinalizer(vm.cleanup_on_provider)
    return vm


@pytest.mark.rhv3
@pytest.mark.uncollectif(
    lambda appliance, provider: appliance.version < "5.9" or provider.one_of(GCEProvider))
@pytest.mark.provider([CloudInfraProvider])
@pytest.mark.parametrize('enable', [False, True], ids=['disabled', 'enabled'])
def test_cockpit_server_role(appliance, provider, setup_provider, new_vm, enable):
    """ The test checks the cockpit "Web Console" button enable and disabled working.

    Polarion:
        assignee: nansari
        initialEstimate: None
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
