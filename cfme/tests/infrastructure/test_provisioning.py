# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.common.vm import VM
from cfme.infrastructure.provider import InfraProvider
from cfme.provisioning import do_vm_provisioning
from cfme.utils import normalize_text
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
from widgetastic.utils import partial_match

pytestmark = [
    pytest.mark.meta(server_roles="+automate +notifier"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.tier(2),
    test_requirements.provision,
    pytest.mark.provider([InfraProvider],
                         required_fields=[['provisioning', 'template'],
                                          ['provisioning', 'host'],
                                          ['provisioning', 'datastore']],
                         scope="module"),
]


@pytest.fixture(scope="function")
def vm_name():
    vm_name = random_vm_name('provt')
    return vm_name


@pytest.mark.rhv1
@pytest.mark.tier(1)
@pytest.mark.parametrize('auto', [True, False], ids=["Auto", "Manual"])
def test_provision_from_template(appliance, setup_provider, provider, vm_name, smtp_test,
                                 request, provisioning, auto):
    """ Tests provisioning from a template

    Metadata:
        test_flag: provision
        suite: infra_provisioning
        rbac:
            roles:
                default:
                evmgroup-super_administrator:
                evmgroup-administrator:
                evmgroup-operator: NoSuchElementException
                evmgroup-auditor: NoSuchElementException
    """

    template = provisioning['template']

    request.addfinalizer(lambda: VM.factory(vm_name, provider).cleanup_on_provider())

    provisioning_data = {
        'catalog': {
            'vm_name': vm_name
        },
        'environment': {
            'vm_name': vm_name,
            'host_name': {'name': provisioning['host']} if not auto else None,
            'datastore_name': {'name': provisioning['datastore']} if not auto else None,
            'automatic_placement': True if auto else None
        },
        'network': {
            'vlan': partial_match(provisioning['vlan'])
        }
    }

    do_vm_provisioning(appliance, template, provider, vm_name, provisioning_data, request,
                       smtp_test, num_sec=900)


@pytest.mark.rhv2
@pytest.mark.parametrize("edit", [True, False], ids=["edit", "approve"])
def test_provision_approval(appliance, setup_provider, provider, vm_name, smtp_test, request,
                            edit, provisioning):
    """ Tests provisioning approval. Tests couple of things.

    * Approve manually
    * Approve by editing the request to conform

    Prerequisities:
        * A provider that can provision.
        * Automate role enabled
        * User with e-mail set so you can receive and view them

    Steps:
        * Create a provisioning request that does not get automatically approved (eg. ``num_vms``
            bigger than 1)
        * Wait for an e-mail to come, informing you that the auto-approval was unsuccessful.
        * Depending on whether you want to do manual approval or edit approval, do:
            * MANUAL: manually approve the request in UI
            * EDIT: Edit the request in UI so it conforms the rules for auto-approval.
        * Wait for an e-mail with approval
        * Wait until the request finishes
        * Wait until an email, informing about finished provisioning, comes.

    Metadata:
        test_flag: provision
        suite: infra_provisioning
    """
    # generate_tests makes sure these have values
    template, host, datastore = map(provisioning.get, ('template', 'host', 'datastore'))

    # It will provision two of them
    vm_names = [vm_name + "001", vm_name + "002"]
    request.addfinalizer(
        lambda: [VM.factory(name, provider).cleanup_on_provider() for name in vm_names])

    provisioning_data = {
        'catalog': {
            'vm_name': vm_name,
            'num_vms': '2'
        },
        'environment': {
            'host_name': {'name': host},
            'datastore_name': {'name': datastore}
        },
        'network': {
            'vlan': partial_match(provisioning['vlan'])
        }
    }

    do_vm_provisioning(appliance, template, provider, vm_name, provisioning_data, request,
                       smtp_test, wait=False)
    wait_for(
        lambda:
        len(filter(
            lambda mail:
            "your request for a new vms was not autoapproved" in normalize_text(mail["subject"]),
            smtp_test.get_emails())) == 1,
        num_sec=90, delay=5)
    wait_for(
        lambda:
        len(filter(
            lambda mail:
            "virtual machine request was not approved" in normalize_text(mail["subject"]),
            smtp_test.get_emails())) == 1,
        num_sec=90, delay=5)
    smtp_test.clear_database()

    cells = {'Description': 'Provision from [{}] to [{}###]'.format(template, vm_name)}
    provision_request = appliance.collections.requests.instantiate(cells=cells)
    navigate_to(provision_request, 'Details')
    if edit:
        # Automatic approval after editing the request to conform
        new_vm_name = vm_name + "-xx"
        modifications = {
            'catalog': {'num_vms': "1", 'vm_name': new_vm_name},
            'Description': 'Provision from [{}] to [{}]'.format(template, new_vm_name)}
        provision_request.edit_request(values=modifications)
        vm_names = [new_vm_name]  # Will be just one now
        request.addfinalizer(
            lambda: VM.factory(new_vm_name, provider).cleanup_on_provider()
        )
    else:
        # Manual approval
        provision_request.approve_request(method='ui', reason="Approved")
        vm_names = [vm_name + "001", vm_name + "002"]  # There will be two VMs
        request.addfinalizer(
            lambda: [VM.factory(name, provider).cleanup_on_provider() for name in vm_names])
    wait_for(
        lambda:
        len(filter(
            lambda mail:
            "your virtual machine configuration was approved" in normalize_text(mail["subject"]),
            smtp_test.get_emails())) == 1,
        num_sec=120, delay=5)
    smtp_test.clear_database()

    # Wait for the VM to appear on the provider backend before proceeding to ensure proper cleanup
    logger.info('Waiting for vms %s to appear on provider %s', ", ".join(vm_names), provider.key)
    wait_for(
        lambda: all(map(provider.mgmt.does_vm_exist, vm_names)),
        handle_exception=True, num_sec=600)

    provision_request.wait_for_request(method='ui')
    msg = "Provisioning failed with the message {}".format(provision_request.row.last_message.text)
    assert provision_request.is_succeeded(method='ui'), msg

    # Wait for e-mails to appear
    def verify():
        return (
            len(filter(
                lambda mail:
                "your virtual machine request has completed vm {}".format(normalize_text(vm_name))
                in normalize_text(mail["subject"]),
                smtp_test.get_emails())) == len(vm_names)
        )
    wait_for(verify, message="email receive check", delay=5)
