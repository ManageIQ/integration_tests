# These tests don't work at the moment, due to the security_groups multi select not working
# in selenium (the group is selected then immediately reset)
import pytest

from cfme.services import requests
from cfme.cloud.provisioning import provisioning_form
from cfme.web_ui import flash
from utils import testgen
from utils.providers import setup_cloud_providers
from utils.randomness import generate_random_string
from utils.log import logger
from utils.wait import wait_for

pytestmark = pytest.mark.fixtureconf(server_roles="+automate")


def pytest_generate_tests(metafunc):
    # Filter out providers without templates defined
    argnames, argvalues, idlist = testgen.cloud_providers(metafunc, 'provisioning')

    new_argvalues = []
    new_idlist = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # Don't know what type of instance to provision, move on
            continue

        # required keys should be a subset of the dict keys set
        if not {'image'}.issubset(args['provisioning'].viewkeys()):
            # Need image for image -> instance provisioning
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append([args[argname] for argname in argnames])

    testgen.checkskip(metafunc, new_argvalues)
    metafunc.parametrize(argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="module")
def setup_providers():
    # Normally function-scoped
    setup_cloud_providers()


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


def test_provision_from_template(setup_providers, vm_name, provider_crud, provider_mgmt,
        provisioning):
    # This is ensured to work by pytest_generate_tests
    image = provisioning['image']['name']

    pytest.sel.force_navigate('clouds_provision_instances', context={
        'provider': provider_crud,
        'template_name': image,
    })

    note = ('Testing provisioning from image %s to vm %s on provider %s' %
        (image, vm_name, provider_crud.key))

    # Currently broken: security group can't be selected with selenium
    provisioning_data = {
        'email': 'image_provisioner@example.com',
        'first_name': 'Image',
        'last_name': 'Provisioner',
        'notes': note,
        'instance_name': vm_name,
        'instance_type': provisioning['instance_type'],
        'availability_zone': provisioning['availability_zone'],
        'security_groups': provisioning['security_group']
    }
    provisioning_form.fill(provisioning_data)
    pytest.sel.click(provisioning_form.submit_button)
    flash.assert_no_errors()

    # Wait for the VM to appear on the provider backend before proceeding to ensure proper cleanup
    logger.info('Waiting for vm %s to appear on provider %s', vm_name, provider_crud.key)
    wait_for(provider_mgmt.does_vm_exist, [vm_name], handle_exception=True, num_sec=600)

    # nav to requests page happens on successful provision
    logger.info('Waiting for cfme provision request for vm %s' % vm_name)
    row_description = 'Provision from [%s] to [%s]' % (image, vm_name)
    cells = {'Description': row_description}

    row, __ = wait_for(requests.wait_for_request, [cells],
        fail_func=requests.reload, num_sec=600, delay=20)
    assert row.last_message.text == 'VM Provisioned Successfully'
