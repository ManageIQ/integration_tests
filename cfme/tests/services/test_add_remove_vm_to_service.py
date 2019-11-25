import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from cfme.automate.simulation import simulate
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE


pytestmark = [
    test_requirements.service,
    pytest.mark.usefixtures('setup_provider_module', 'catalog_item', 'uses_infra_providers'),
    pytest.mark.long_running,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.tier(3),
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE, scope="module"),
]


@pytest.fixture(scope='function')
def new_vm(appliance, provider, setup_provider, small_template_modscope):
    """Fixture to provision and delete vm on the provider"""
    vm_name = fauxfactory.gen_alphanumeric(18, start="test_service_")
    collection = appliance.provider_based_collection(provider)

    vm = collection.instantiate(vm_name, provider, small_template_modscope.name)
    vm.create_on_provider(find_in_cfme=True, timeout=700, allow_skip="default")
    yield vm
    vm.cleanup_on_provider()
    provider.refresh_provider_relationships()


@pytest.fixture(scope="function")
def copy_domain(request, appliance):
    dc = DomainCollection(appliance)
    domain = dc.create(name=fauxfactory.gen_alphanumeric(12, start="domain_"), enabled=True)
    request.addfinalizer(domain.delete_if_exists)
    dc.instantiate(name='ManageIQ')\
        .namespaces.instantiate(name='System')\
        .classes.instantiate(name='Request')\
        .copy_to(domain)
    return domain


@pytest.mark.ignore_stream("upstream")
def test_add_vm_to_service(service_vm, request, copy_domain, new_vm, appliance):
    """Tests adding vm to service

    Metadata:
        test_flag: provision

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        tags: service
    """

    myservice, _ = service_vm
    method_torso = """
    def add_to_service
        vm      = $evm.root['vm']
        service = $evm.vmdb('service').find_by_name('{}')
        user    = $evm.root['user']

    if service && vm
        $evm.log('info', "XXXXXXXX Attaching Service to VM: [#{{service.name}}][#{{vm.name}}]")
        vm.add_to_service(service)
        vm.owner = user if user
        vm.group = user.miq_group if user
    end
    end

    $evm.log("info", "Listing Root Object Attributes:")
    $evm.log("info", "===========================================")

    add_to_service
    """.format(myservice.name)
    method = copy_domain\
        .namespaces.instantiate(name='System')\
        .classes.instantiate(name='Request')\
        .methods.create(name='InspectMe', location='inline', script=method_torso)

    request.addfinalizer(method.delete_if_exists)
    simulate(
        appliance=appliance,
        instance="Request",
        message="create",
        request=method.name,
        target_type='VM and Instance',
        target_object=new_vm.name,
        execute_methods=True
    )
    myservice.check_vm_add(new_vm)
