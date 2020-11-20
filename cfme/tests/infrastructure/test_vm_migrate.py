import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log_validator import LogValidator


pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    test_requirements.vm_migrate,
    pytest.mark.tier(2),
    pytest.mark.provider([VMwareProvider, RHEVMProvider], scope='module')
]


@pytest.mark.meta(
    blockers=[
        BZ(
            1879912,
            forced_streams=["5.11"],
            unblock=lambda provider: (
                not (provider.one_of(RHEVMProvider) and provider.version == 4.2)
            ),
        )
    ]
)
def test_vm_migrate(appliance, create_vm, provider):
    """Tests migration of a vm

    Metadata:
        test_flag: migrate, provision

    Polarion:
        assignee: dgaikwad
        casecomponent: Provisioning
        initialEstimate: 1/4h
    """
    # auto_test_services should exist to test migrate VM
    view = navigate_to(create_vm, 'Details')
    vm_host = view.entities.summary('Relationships').get_text_of('Host')
    hosts = [vds.name for vds in provider.hosts.all() if vds.name not in vm_host]
    if hosts:
        migrate_to = hosts[0]
    else:
        pytest.skip("There is only one host in the provider")
    create_vm.migrate_vm("email@xyz.com", "first", "last", host=migrate_to)
    request_description = create_vm.name
    cells = {'Description': request_description, 'Request Type': 'Migrate'}
    migrate_request = appliance.collections.requests.instantiate(request_description, cells=cells,
                                                                 partial_check=True)
    migrate_request.wait_for_request(method='ui')
    msg = f"Request failed with the message {migrate_request.row.last_message.text}"
    assert migrate_request.is_succeeded(method='ui'), msg


@pytest.mark.tier(3)
@pytest.mark.meta(automates=[1478462])
def test_vm_migrate_should_create_notifications_when_migrations_fail(appliance,
                                                                     create_vm, provider):
    """
    Polarion:
        assignee: dgaikwad
        casecomponent: WebUI
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.10
        tags: service
        caseposneg: negative
        testSteps:
            1. add provider to appliance
            2. create vm
            3. migrate vm, use same host and datastore is None
        expectedResults:
            1.
            2.
            3. check error on UI and in the log file.
    Bugzilla:
        1478462
    """
    view = navigate_to(create_vm, 'Details')
    vm_host = view.entities.summary('Relationships').get_text_of('Host')
    hosts = [vds.name for vds in provider.hosts.all() if vds.name in vm_host]
    err_msg = ("Status [Error Migrating VM] Message")
    with LogValidator('/var/www/miq/vmdb/log/automation.log',
                      matched_patterns=[err_msg],
                      hostname=appliance.hostname).waiting(timeout=900):
        create_vm.migrate_vm(
            fauxfactory.gen_email(),
            fauxfactory.gen_string("alphanumeric", 5),
            fauxfactory.gen_string("alphanumeric", 5),
            hosts[0],
            "<None>",
        )
        request_description = create_vm.name
        cells = {'Description': request_description, 'Request Type': 'Migrate'}
        migrate_request = appliance.collections.requests.instantiate(
            request_description,
            cells=cells,
            partial_check=True
        )
        migrate_request.wait_for_request(method='ui')
        assert not migrate_request.is_succeeded(method='ui'), "VM migration does not failed"
        assert err_msg in migrate_request.row.last_message.text, (
            migrate_request.row.last_message.text
        )
