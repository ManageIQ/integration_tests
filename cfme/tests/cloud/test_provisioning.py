# These tests don't work at the moment, due to the security_groups multi select not working
# in selenium (the group is selected then immediately reset)
import pytest

import cfme.cloud.provisioning
assert cfme.cloud.provisioning
from cfme.cloud.instance import instance_factory
from cfme.cloud.provider import OpenStackProvider
from cfme.fixtures import pytest_selenium as sel
from utils import testgen
from utils.randomness import generate_random_string

pytestmark = [pytest.mark.fixtureconf(server_roles="+automate"),
              pytest.mark.usefixtures('server_roles')]


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


@pytest.fixture(scope="function")
def vm_name(request, provider_mgmt):
    vm_name = 'test_image_prov_%s' % generate_random_string()
    return vm_name


@pytest.mark.bugzilla(1131330)
def test_provision_from_template(request, setup_provider, provider_crud, provisioning, vm_name):
    image = provisioning['image']['name']
    note = ('Testing provisioning from image %s to vm %s on provider %s' %
            (image, vm_name, provider_crud.key))

    instance = instance_factory(vm_name, provider_crud, image)

    request.addfinalizer(instance.delete_from_provider)

    inst_args = {
        'email': 'image_provisioner@example.com',
        'first_name': 'Image',
        'last_name': 'Provisioner',
        'notes': note,
        'instance_type': provisioning['instance_type'],
        'availability_zone': provisioning['availability_zone'],
        'security_groups': [provisioning['security_group']],
        'guest_keypair': provisioning['guest_keypair']
    }

    if isinstance(provider_crud, OpenStackProvider):
        inst_args['cloud_network'] = provisioning['cloud_network']

    sel.force_navigate("clouds_instances_by_provider")
    instance.create(**inst_args)
