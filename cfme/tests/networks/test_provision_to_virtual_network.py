import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.common.vm import VM
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.provisioning import do_vm_provisioning
from cfme.utils.generators import random_vm_name
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.provider([RHEVMProvider],
                         required_fields=[['provisioning', 'template']],
                         scope='module'
                         ),
    pytest.mark.uncollectif(lambda provider: provider.version < 4.2,
                            reason='ovn functionality is limited in 4.1'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.ignore_stream('5.8'),
    test_requirements.provision,
]


@pytest.fixture(scope='function')
def network(provider, appliance):
    """Test adding cloud network in ui."""
    test_name = 'test_network_{}'.format(fauxfactory.gen_alphanumeric(6))
    net_manager = '{} Network Manager'.format(provider.name)
    collection = appliance.collections.network_providers
    network_provider = collection.instantiate(name=net_manager)
    collection = appliance.collections.cloud_networks
    ovn_network = collection.create(test_name, 'tenant', network_provider, net_manager, 'None')

    yield ovn_network
    if ovn_network.exists:
        ovn_network.delete()


@pytest.mark.rhv1
def test_provision_vm_to_virtual_network(appliance, setup_provider, provider,
                                         request, provisioning, network):
    """ Tests provisioning a vm from a template to a virtual network

    Metadata:
        test_flag: provision
    """
    vm_name = random_vm_name('provd')
    request.addfinalizer(
        lambda: appliance.rest_api.collections.vms.get(name=vm_name).action.delete())

    template = provisioning['template']
    provisioning_data = {
        'catalog': {
            'vm_name': vm_name
        },
        'environment': {
            'vm_name': vm_name,
            'automatic_placement': True
        },
        'network': {
            'vlan': partial_match(network.name)
        }
    }
    wait_for(
        do_vm_provisioning,
        [appliance, template, provider, vm_name, provisioning_data, request],
        {'num_sec': 900, 'smtp_test': False},
        handle_exception=True,
        delay=50,
        num_sec=900,
        fail_func=appliance.server.browser.refresh,
        message='Cannot do provision for vm {}.'.format(vm_name)
    )
