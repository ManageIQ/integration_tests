# -*- coding: utf-8 -*-
import pytest

from utils.providers import setup_provider
from cfme.infrastructure.virtual_machines import Vm
from cfme.services import requests
from utils.wait import wait_for
from utils import testgen
from utils.log import logger
from utils.randomness import generate_random_string

pytestmark = [
    pytest.mark.fixtureconf(server_roles="+automate"),
    pytest.mark.usefixtures('logged_in', 'vm_name', 'uses_infra_providers')
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

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture()
def provider_init(provider_key):
    try:
        setup_provider(provider_key)
    except Exception:
        pytest.skip("It's not possible to set up this provider, therefore skipping")


@pytest.fixture(scope="function")
def vm_name():
    vm_name = 'test_cloning_{}'.format(generate_random_string())
    return vm_name


def cleanup_vm(vm_name, provider_key, provider_mgmt):
    try:
        logger.info('Cleaning up VM %s on provider %s' % (vm_name, provider_key))
        provider_mgmt.delete_vm(vm_name + "_0001")
    except:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM %s on provider %s' % (vm_name, provider_key))


@pytest.mark.long_running
def test_vm_clone(provisioning, provider_init, provider_crud,
                  provider_mgmt, request, vm_name, provider_key):
    request.addfinalizer(lambda: cleanup_vm(vm_name, provider_key, provider_mgmt))
    vm = Vm("vmtest", provider_crud)
    vm.clone_vm("email@xyz.com", "first", "last", vm_name)
    row_description = 'Clone from [vmtest] to [%s]' % (vm_name)
    cells = {'Request Type': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells],
        fail_func=requests.reload, num_sec=3500, delay=20)
    assert row.last_message.text == 'Vm Provisioned Successfully'
