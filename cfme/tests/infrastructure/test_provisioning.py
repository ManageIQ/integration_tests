import pytest

from cfme.infrastructure.provisioning import provisioning_form
from cfme.services import requests
from cfme.web_ui import flash
from utils import testgen
from utils.providers import setup_infrastructure_providers
from utils.randomness import generate_random_string
from utils.log import logger
from utils.wait import wait_for

pytestmark = [
    pytest.mark.fixtureconf(server_roles="+automate"),
    pytest.mark.usefixtures('server_roles', 'uses_infra_providers')
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc, 'provisioning')

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # No provisioning data available
            continue

        # required keys should be a subset of the dict keys set
        if not {'template', 'host', 'datastore'}.issubset(args['provisioning'].viewkeys()):
            # Need all three for template provisioning
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.checkskip(metafunc, new_argvalues)
    metafunc.parametrize(argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="module")
def setup_providers():
    # Normally function-scoped
    setup_infrastructure_providers()


@pytest.yield_fixture(scope="function")
def vm_name(provider_key, provider_mgmt):
    # also tries to delete the VM that gets made with this name
    vm_name = 'provtest-%s' % generate_random_string()
    yield vm_name
    try:
        logger.info('Cleaning up VM %s on provider %s' % (vm_name, provider_key))
        provider_mgmt.delete_vm(vm_name)
    except:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM %s on provider %s' % (vm_name, provider_key))


def test_provision_from_template(setup_providers,
        provider_crud, provider_type, provider_mgmt, provisioning, vm_name):
    # generate_tests makes sure these have values
    template, host, datastore = map(provisioning.get, ('template', 'host', 'datastore'))
    pytest.sel.force_navigate('infrastructure_provision_vms', context={
        'provider': provider_crud,
        'template_name': template,
    })

    note = ('template %s to vm %s on provider %s' %
        (template, vm_name, provider_crud.key))
    provisioning_data = {
        'email': 'template_provisioner@example.com',
        'first_name': 'Template',
        'last_name': 'Provisioner',
        'notes': note,
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

    provisioning_form.fill(provisioning_data)
    pytest.sel.click(provisioning_form.submit_button)
    flash.assert_no_errors()

    # Wait for the VM to appear on the provider backend before proceeding to ensure proper cleanup
    logger.info('Waiting for vm %s to appear on provider %s', vm_name, provider_crud.key)
    wait_for(provider_mgmt.does_vm_exist, [vm_name], handle_exception=True, num_sec=600)

    # nav to requests page happens on successful provision
    logger.info('Waiting for cfme provision request for vm %s' % vm_name)
    row_description = 'Provision from [%s] to [%s]' % (template, vm_name)
    cells = {'Description': row_description}

    row, __ = wait_for(requests.wait_for_request, [cells],
        fail_func=requests.reload, num_sec=600, delay=20)
    assert row.last_message.text == 'VM Provisioned Successfully'
