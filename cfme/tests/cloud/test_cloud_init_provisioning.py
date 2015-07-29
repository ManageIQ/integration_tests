# -*- coding: utf-8 -*-
# These tests don't work at the moment, due to the security_groups multi select not working
# in selenium (the group is selected then immediately reset)
import fauxfactory
import pytest

from cfme.cloud.instance import instance_factory
from cfme.cloud.provider import OpenStackProvider
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure.pxe import get_template_from_config
from utils.conf import cfme_data
from utils import testgen, ssh
from utils.wait import wait_for

pytestmark = [pytest.mark.meta(server_roles="+automate")]


def pytest_generate_tests(metafunc):
    # Filter out providers without templates defined
    argnames, argvalues, idlist = testgen.cloud_providers(metafunc, 'provisioning')
    argnames = argnames + ['cloud_init_template']

    new_argvalues = []
    new_idlist = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # Don't know what type of instance to provision, move on
            continue

        if not {'ci-template', 'ci-username', 'ci-pass', 'image'}.issubset(
                args['provisioning'].viewkeys()):
            # Need all for template provisioning
            continue

        cloud_init_template = args['provisioning']['ci-template']
        if cloud_init_template not in cfme_data.get('customization_templates', {}).keys():
            continue

        argvalues[i].append(get_template_from_config(cloud_init_template))

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="module")
def setup_ci_template(cloud_init_template):
    if not cloud_init_template.exists():
        cloud_init_template.create()


@pytest.fixture(scope="function")
def vm_name(request):
    vm_name = 'test_image_prov_%s' % fauxfactory.gen_alphanumeric()
    return vm_name


def test_provision_cloud_init(request, setup_provider, provider, provisioning,
                              setup_ci_template, vm_name):
    """ Tests provisioning from a template with cloud_init

    Metadata:
        test_flag: cloud_init, provision
    """
    image = provisioning.get('ci-image', None) or provisioning['image']['name']
    note = ('Testing provisioning from image %s to vm %s on provider %s' %
            (image, vm_name, provider.key))

    mgmt_system = provider.mgmt

    instance = instance_factory(vm_name, provider, image)

    request.addfinalizer(instance.delete_from_provider)

    inst_args = {
        'email': 'image_provisioner@example.com',
        'first_name': 'Image',
        'last_name': 'Provisioner',
        'notes': note,
        'instance_type': provisioning['instance_type'],
        'availability_zone': provisioning['availability_zone'],
        'security_groups': [provisioning['security_group']],
        'guest_keypair': provisioning['guest_keypair'],
        'custom_template': {'name': [provisioning['ci-template']]},
    }

    if isinstance(provider, OpenStackProvider):
        floating_ip = mgmt_system.get_first_floating_ip()
        inst_args['cloud_network'] = provisioning['cloud_network']
        inst_args['public_ip_address'] = floating_ip

    sel.force_navigate("clouds_instances_by_provider")
    instance.create(**inst_args)

    connect_ip, tc = wait_for(mgmt_system.get_ip_address, [vm_name], num_sec=300,
                              handle_exception=True)

    # Check that we can at least get the uptime via ssh this should only be possible
    # if the username and password have been set via the cloud-init script so
    # is a valid check
    sshclient = ssh.SSHClient(hostname=connect_ip, username=provisioning['ci-username'],
                              password=provisioning['ci-pass'])
    wait_for(sshclient.uptime, num_sec=200, handle_exception=True)
