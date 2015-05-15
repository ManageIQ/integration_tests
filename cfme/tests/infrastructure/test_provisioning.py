# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.provisioning import cleanup_vm, do_vm_provisioning
from cfme.services import requests
from utils import normalize_text, testgen
from utils.log import logger
from utils.providers import setup_provider
from utils.wait import wait_for

pytestmark = [
    pytest.mark.meta(server_roles="+automate +notifier"),
    pytest.mark.usefixtures('uses_infra_providers')
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(
        metafunc, 'provisioning', template_location=["provisioning", "template"])

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # No provisioning data available
            continue

        if args['provider_type'] == "scvmm":
            continue

        # required keys should be a subset of the dict keys set
        if not {'template', 'host', 'datastore'}.issubset(args['provisioning'].viewkeys()):
            # Need all three for template provisioning
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture()
def provider_init(provider_key):
    try:
        setup_provider(provider_key)
    except Exception:
        pytest.skip("It's not possible to set up this provider, therefore skipping")


@pytest.fixture(scope="function")
def vm_name():
    vm_name = 'test_tmpl_prov_%s' % fauxfactory.gen_alphanumeric()
    return vm_name


def test_provision_from_template(provider_init, provider_key, provider_crud, provider_type,
                                 provider_mgmt, provisioning, vm_name, smtp_test, request):
    """ Tests provisioning from a template

    Metadata:
        test_flag: provision
        suite: infra_provisioning
    """

    # generate_tests makes sure these have values
    template, host, datastore = map(provisioning.get, ('template', 'host', 'datastore'))

    request.addfinalizer(lambda: cleanup_vm(vm_name, provider_key, provider_mgmt))

    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]}
    }

    # Same thing, different names. :\
    if provider_type == 'rhevm':
        provisioning_data['provision_type'] = 'Native Clone'
    elif provider_type == 'virtualcenter':
        provisioning_data['provision_type'] = 'VMware'

    try:
        provisioning_data['vlan'] = provisioning['vlan']
    except KeyError:
        # provisioning['vlan'] is required for rhevm provisioning
        if provider_type == 'rhevm':
            raise pytest.fail('rhevm requires a vlan value in provisioning info')

    do_vm_provisioning(template, provider_crud, vm_name, provisioning_data, request,
                       provider_mgmt, provider_key, smtp_test, num_sec=900)


def test_provision_approval(provider_init, provider_key, provider_crud, provider_type,
                            provider_mgmt, provisioning, vm_name, smtp_test, request):
    """ Tests provisioning approval

    Metadata:
        test_flag: provision
        suite: infra_provisioning
    """
    # generate_tests makes sure these have values
    template, host, datastore = map(provisioning.get, ('template', 'host', 'datastore'))

    # It will provision two of them
    vm_names = [vm_name + "001", vm_name + "002"]
    request.addfinalizer(
        lambda: [cleanup_vm(vmname, provider_key, provider_mgmt) for vmname in vm_names])

    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]},
        'num_vms': "2",
    }

    # Same thing, different names. :\
    if provider_type == 'rhevm':
        provisioning_data['provision_type'] = 'Native Clone'
    elif provider_type == 'virtualcenter':
        provisioning_data['provision_type'] = 'VMware'

    try:
        provisioning_data['vlan'] = provisioning['vlan']
    except KeyError:
        # provisioning['vlan'] is required for rhevm provisioning
        if provider_type == 'rhevm':
            raise pytest.fail('rhevm requires a vlan value in provisioning info')

    do_vm_provisioning(template, provider_crud, vm_name, provisioning_data, request,
                       provider_mgmt, provider_key, smtp_test, wait=False)
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
    requests.approve_request(cells, "Approved")
    wait_for(
        lambda:
        len(filter(
            lambda mail:
            "your virtual machine configuration was approved" in normalize_text(mail["subject"]),
            smtp_test.get_emails())) > 0,
        num_sec=90, delay=5)

    # Wait for the VM to appear on the provider backend before proceeding to ensure proper cleanup
    logger.info(
        'Waiting for vms "{}" to appear on provider {}'.format(
            ", ".join(vm_names), provider_crud.key))
    wait_for(
        lambda: all(map(provider_mgmt.does_vm_exist, vm_names)),
        handle_exception=True, num_sec=600)

    row, __ = wait_for(requests.wait_for_request, [cells],
                       fail_func=requests.reload, num_sec=1500, delay=20)
    assert normalize_text(row.last_message.text) == "request complete"

    # Wait for e-mails to appear
    def verify():
        return (
            len(filter(
                lambda mail:
                "your virtual machine request has completed vm {}".format(normalize_text(vm_name))
                in normalize_text(mail["subject"]),
                smtp_test.get_emails())) == 2
        )

    wait_for(verify, message="email receive check", delay=5)
