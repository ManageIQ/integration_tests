import fauxfactory
import pytest
from widgetastic.utils import partial_match

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.networks.provider import NetworkProvider
from cfme.provisioning import do_vm_provisioning
from cfme.utils.blockers import BZ
from cfme.utils.blockers import GH
from cfme.utils.generators import random_vm_name
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.provider([RHEVMProvider],
                         required_fields=[['provisioning', 'template']],
                         scope='module'
                         ),
    pytest.mark.usefixtures('setup_provider'),
    test_requirements.provision,
]


@pytest.fixture(scope='function')
def network(provider, appliance):
    """Adding cloud network in ui."""
    test_name = 'test_network_{}'.format(fauxfactory.gen_alphanumeric(6))
    net_manager = '{} Network Manager'.format(provider.name)

    collection = appliance.collections.network_providers
    network_provider = collection.instantiate(prov_class=NetworkProvider, name=net_manager)

    collection = appliance.collections.cloud_networks
    ovn_network = collection.create(test_name, 'tenant', network_provider, net_manager, 'None')

    yield ovn_network
    if ovn_network.exists:
        ovn_network.delete()


@pytest.mark.rhv1
@test_requirements.rhev
@pytest.mark.meta(
    blockers=[
        GH('ManageIQ/integration_tests:8128'),
        BZ(1649886, unblock=lambda provider: not provider.one_of(RHEVMProvider))
    ]
)
def test_provision_vm_to_virtual_network(appliance, setup_provider, provider,
                                         request, provisioning, network):
    """ Tests provisioning a vm from a template to a virtual network

    Metadata:
        test_flag: provision

    Polarion:
        assignee: anikifor
        casecomponent: Provisioning
        initialEstimate: 1/4h
    """
    vm_name = random_vm_name('provd')

    def _cleanup():
        vm = appliance.collections.infra_vms.instantiate(vm_name, provider)
        vm.cleanup_on_provider()

    request.addfinalizer(_cleanup)

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
        {'num_sec': 900},
        handle_exception=True,
        delay=50,
        num_sec=900,
        fail_func=appliance.server.browser.refresh,
        message='Cannot do provision for vm {}.'.format(vm_name)
    )
