# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.common.provider import cleanup_vm
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.provisioning import do_vm_provisioning
from cfme.services import requests
from cfme.web_ui import fill
from utils import normalize_text, testgen
from utils.blockers import BZ
from utils.generators import random_vm_name
from utils.log import logger
from utils.wait import wait_for

pytestmark = [
    pytest.mark.meta(server_roles="+automate +notifier"),
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.meta(blockers=[
        BZ(
            1265466,
            unblock=lambda provider: not provider.one_of(RHEVMProvider))
    ]),
    pytest.mark.tier(2),
    test_requirements.provision
]


pytest_generate_tests = testgen.generate([InfraProvider], required_fields=[
    ['provisioning', 'template'],
    ['provisioning', 'host'],
    ['provisioning', 'datastore']
], scope="module")


@pytest.fixture(scope="function")
def vm_name():
    vm_name = random_vm_name('provt')
    return vm_name


@pytest.mark.tier(1)
@pytest.mark.skipif(lambda provider:
                    provider.type == 'virtualcenter' and BZ('1422953', forced_streams='5.7').blocks,
                    reason="Affected by 1422953, cannot test for VMware")
def test_provision_from_template(rbac_role, configure_ldap_auth_mode, setup_provider, provider,
        vm_name, smtp_test, request, provisioning):
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

    # generate_tests makes sure these have values
    template, host, datastore = map(provisioning.get, ('template', 'host', 'datastore'))

    request.addfinalizer(lambda: cleanup_vm(vm_name, provider))

    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]}
    }

    # Same thing, different names. :\
    if provider.type == 'rhevm':
        provisioning_data['provision_type'] = 'Native Clone'
    elif provider.type == 'virtualcenter':
        provisioning_data['provision_type'] = 'VMware'

    try:
        provisioning_data['vlan'] = provisioning['vlan']
    except KeyError:
        # provisioning['vlan'] is required for rhevm provisioning
        if provider.type == 'rhevm':
            raise pytest.fail('rhevm requires a vlan value in provisioning info')

    do_vm_provisioning(template, provider, vm_name, provisioning_data, request, smtp_test,
                       num_sec=900)


@pytest.mark.skipif(lambda provider:
                    provider.type == 'virtualcenter' and BZ('1422953', forced_streams='5.7').blocks,
                    reason="Affected by 1422953, cannot test for VMware")
@pytest.mark.parametrize("edit", [True, False], ids=["edit", "approve"])
def test_provision_approval(
        setup_provider, provider, vm_name, smtp_test, request, edit, provisioning):
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
        lambda: [cleanup_vm(vmname, provider) for vmname in vm_names])

    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]},
        'num_vms': "2",
    }

    # Same thing, different names. :\
    if provider.type == 'rhevm':
        provisioning_data['provision_type'] = 'Native Clone'
    elif provider.type == 'virtualcenter':
        provisioning_data['provision_type'] = 'VMware'

    try:
        provisioning_data['vlan'] = provisioning['vlan']
    except KeyError:
        # provisioning['vlan'] is required for rhevm provisioning
        if provider.type == 'rhevm':
            raise pytest.fail('rhevm requires a vlan value in provisioning info')

    do_vm_provisioning(template, provider, vm_name, provisioning_data, request, smtp_test,
                       wait=False)
    wait_for(
        lambda:
        len(filter(
            lambda mail:
            "your request for a new vms was not autoapproved" in normalize_text(mail["subject"]),
            smtp_test.get_emails())) > 0,
        num_sec=90, delay=5)
    wait_for(
        lambda:
        len(filter(
            lambda mail:
            "virtual machine request was not approved" in normalize_text(mail["subject"]),
            smtp_test.get_emails())) > 0,
        num_sec=90, delay=5)

    cells = {'Description': 'Provision from [{}] to [{}###]'.format(template, vm_name)}
    wait_for(lambda: requests.go_to_request(cells), num_sec=80, delay=5)
    if edit:
        # Automatic approval after editing the request to conform
        with requests.edit_request(cells) as form:
            fill(form.num_vms, "1")
            new_vm_name = vm_name + "-xx"
            fill(form.vm_name, new_vm_name)
        vm_names = [new_vm_name]  # Will be just one now
        cells = {'Description': 'Provision from [{}] to [{}]'.format(template, new_vm_name)}
        request.addfinalizer(
            lambda: cleanup_vm(new_vm_name, provider))
    else:
        # Manual approval
        requests.approve_request(cells, "Approved")
        vm_names = [vm_name + "001", vm_name + "002"]  # There will be two VMs
        request.addfinalizer(
            lambda: [cleanup_vm(vmname, provider) for vmname in vm_names])
    wait_for(
        lambda:
        len(filter(
            lambda mail:
            "your virtual machine configuration was approved" in normalize_text(mail["subject"]),
            smtp_test.get_emails())) > 0,
        num_sec=120, delay=5)

    # Wait for the VM to appear on the provider backend before proceeding to ensure proper cleanup
    logger.info('Waiting for vms %s to appear on provider %s', ", ".join(vm_names), provider.key)
    wait_for(
        lambda: all(map(provider.mgmt.does_vm_exist, vm_names)),
        handle_exception=True, num_sec=600)

    row, __ = wait_for(requests.wait_for_request, [cells],
                       fail_func=requests.reload, num_sec=1500, delay=20)
    assert normalize_text(row.status.text) == 'ok' \
        and normalize_text(row.request_state.text) == 'finished'

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
