import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.gce import GCEProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.markers.env_markers.provider import providers
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.providers import ProviderFilter
from cfme.utils.wait import wait_for

pytestmark = [test_requirements.cockpit]


@pytest.mark.provider(
    gen_func=providers,
    filters=[
        ProviderFilter(classes=[CloudProvider, InfraProvider]),
        ProviderFilter(classes=[GCEProvider], inverted=True)
    ],
    selector=ONE_PER_TYPE,
)
@pytest.mark.parametrize('enable', [False, True], ids=['disabled', 'enabled'])
@pytest.mark.parametrize('create_vm', ['small_template'], indirect=True)
def test_cockpit_server_role(appliance, provider, setup_provider, create_vm, enable):
    """ The test checks the cockpit "Web Console" button enable and disabled working.

    Metadata:
        test_flag: inventory

    Polarion:
        assignee: nansari
        caseimportance: medium
        casecomponent: Appliance
        initialEstimate: 1/4h
    """

    if enable:
        appliance.server.settings.enable_server_roles('cockpit_ws')
        wait_for(lambda: appliance.server_roles['cockpit_ws'] is True, delay=20, timeout=300)
        view = navigate_to(create_vm, 'Details')
        assert view.toolbar.access.item_enabled('Web Console')
        appliance.server.settings.disable_server_roles('cockpit_ws')
    else:
        appliance.server.settings.disable_server_roles('cockpit_ws')
        wait_for(lambda: appliance.server_roles['cockpit_ws'] is False, delay=20, timeout=300)
        view = navigate_to(create_vm, 'Details')
        access = view.toolbar.access
        assert not access.is_enabled or not access.item_enabled('Web Console')
