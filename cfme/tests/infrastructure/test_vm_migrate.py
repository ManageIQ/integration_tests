import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    test_requirements.vm_migrate,
    pytest.mark.tier(2),
    pytest.mark.provider([VMwareProvider, RHEVMProvider], scope='module')
]


@pytest.fixture()
def new_vm(setup_provider, provider):
    """Fixture to provision appliance to the provider being tested if necessary"""
    vm_name = random_vm_name(context='migrate')
    try:
        template_name = provider.data.templates.small_template.name
    except AttributeError:
        pytest.skip('Could not find templates.small_template.name in provider yaml: {}'
                    .format(provider.data))

    vm = provider.appliance.collections.infra_vms.instantiate(vm_name, provider, template_name)

    if not provider.mgmt.does_vm_exist(vm_name):
        vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    yield vm
    vm.cleanup_on_provider()


@pytest.mark.rhv1
def test_vm_migrate(appliance, new_vm, provider):
    """Tests migration of a vm

    Metadata:
        test_flag: migrate, provision

    Polarion:
        assignee: dgaikwad
        casecomponent: Provisioning
        initialEstimate: 1/4h
    """
    # auto_test_services should exist to test migrate VM
    view = navigate_to(new_vm, 'Details')
    vm_host = view.entities.summary('Relationships').get_text_of('Host')
    hosts = [vds.name for vds in provider.hosts.all() if vds.name not in vm_host]
    if hosts:
        migrate_to = hosts[0]
    else:
        pytest.skip("There is only one host in the provider")
    new_vm.migrate_vm("email@xyz.com", "first", "last", host=migrate_to)
    request_description = new_vm.name
    cells = {'Description': request_description, 'Request Type': 'Migrate'}
    migrate_request = appliance.collections.requests.instantiate(request_description, cells=cells,
                                                                 partial_check=True)
    migrate_request.wait_for_request(method='ui')
    msg = "Request failed with the message {}".format(migrate_request.row.last_message.text)
    assert migrate_request.is_succeeded(method='ui'), msg


@pytest.mark.manual
@pytest.mark.tier(3)
def test_vm_migrate_should_create_notifications_when_migrations_fail():
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: WebUI
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.10
        tags: service
    Bugzilla:
        1478462
    """
    pass
