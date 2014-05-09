# These tests don't work at the moment, due to the security_groups multi select not working
# in selenium (the group is selected then immediately reset)
import pytest
from utils import testgen
from utils.providers import setup_cloud_providers
from utils.randomness import generate_random_string
from utils.log import logger
from cfme.cloud import provisioning as prov

pytestmark = [pytest.mark.fixtureconf(server_roles="+automate"),
              pytest.mark.usefixtures('server_roles', 'setup_providers')]


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

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="module")
def setup_providers():
    # Normally function-scoped
    setup_cloud_providers()


@pytest.yield_fixture(scope="function")
def instance(setup_providers, provider_key, provider_mgmt, provisioning, provider_crud):
    # tries to delete the VM that gets created here
    vm_name = 'provtest-%s' % generate_random_string()
    image = provisioning['image']['name']
    note = ('Testing provisioning from image %s to vm %s on provider %s' %
        (image, vm_name, provider_crud.key))

    instance = prov.Instance(
        name=vm_name,
        email='image_provisioner@example.com',
        first_name='Image',
        last_name='Provisioner',
        notes=note,
        instance_type=provisioning['instance_type'],
        availability_zone=provisioning['availability_zone'],
        security_groups=[provisioning['security_group']],
        provider_mgmt=provider_mgmt,
        provider=provider_crud,
        guest_keypair="shared",
        template=prov.Template(image))
    instance.create()
    yield instance
    try:
        logger.info('Cleaning up VM %s on provider %s' % (vm_name, provider_key))
        provider_mgmt.delete_vm(vm_name)
    except:
        # The mgmt_sys classes raise Exception :\
        logger.warning('Failed to clean up VM %s on provider %s' % (vm_name, provider_key))


def test_provision_from_template(setup_providers, provider_mgmt, instance):
    assert(provider_mgmt.is_vm_running(instance.name))


def test_stop_start(provider_mgmt, instance):
    instance.stop()
    assert(provider_mgmt.is_vm_stopped(instance.name))
    instance.start()
    assert(provider_mgmt.is_vm_running(instance.name))


def test_terminate(provider_mgmt, instance):
    instance.terminate()
    assert(provider_mgmt.is_vm_state(instance.name,
                                     provider_mgmt.states['deleted']))
