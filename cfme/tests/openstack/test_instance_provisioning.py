import fauxfactory
import pytest
from cfme import test_requirements
from cfme.automate import explorer as automate
from cfme.cloud.instance import Instance
from cfme.cloud.provider import CloudProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from utils import testgen
from utils.generators import random_vm_name
from utils.log import logger
from utils.wait import wait_for, RefreshTimer


pytestmark = [pytest.mark.meta(server_roles="+automate"),
              test_requirements.provision, pytest.mark.tier(2)]


pytest_generate_tests = testgen.generate(
    [CloudProvider], required_fields=[['provisioning', 'image']], scope="function")


@pytest.fixture(scope="function")
def testing_instance(request, setup_provider, provider, provisioning, vm_name):
    """ Fixture to prepare instance parameters for provisioning
    """
    image = provisioning['image']['name']
    note = ('Testing provisioning from image {} to vm {} on provider {}'.format(
        image, vm_name, provider.key))
    instance = Instance.factory(vm_name, provider, image)

    request.addfinalizer(instance.delete_from_provider)

    inst_args = {
        'email': 'image_provisioner@example.com',
        'first_name': 'Image',
        'last_name': 'Provisioner',
        'notes': note,
    }
    if isinstance(provider, OpenStackProvider):
        inst_args['cloud_network'] = provisioning['cloud_network']

    return instance, inst_args


@pytest.fixture(scope="function")
def vm_name(request, provider):
    return random_vm_name('prov')


def test_provision_from_template(request, setup_provider, provider, testing_instance, soft_assert):
    """ Tests instance provision from template

    Metadata:
        test_flag: provision
    """
    instance, inst_args = testing_instance
    instance.create(**inst_args)
    instance.wait_to_appear(timeout=800)
    provider.refresh_provider_relationships()
    logger.info("Refreshing provider relationships and power states")
    refresh_timer = RefreshTimer(time_for_refresh=300)
    wait_for(provider.is_refreshed,
             [refresh_timer],
             message="is_refreshed",
             num_sec=1000,
             delay=60,
             handle_exception=True)
    soft_assert(instance.does_vm_exist_on_provider(), "Instance wasn't provisioned")


@pytest.fixture(scope="module")
def domain(request):
    domain = automate.Domain(name=fauxfactory.gen_alphanumeric(), enabled=True)
    domain.create()
    request.addfinalizer(lambda: domain.delete() if domain.exists() else None)
    return domain


@pytest.fixture(scope="module")
def cls(request, domain):
    tcls = automate.Class(name="Methods",
        namespace=automate.Namespace.make_path("Cloud", "VM", "Provisioning", "StateMachines",
            parent=domain, create_on_init=True))
    tcls.create()
    request.addfinalizer(lambda: tcls.delete() if tcls.exists() else None)
    return tcls


@pytest.fixture(scope="module")
def copy_domains(domain):
    methods = ['openstack_PreProvision', 'openstack_CustomizeRequest']
    for method in methods:
        ocls = automate.Class(name="Methods",
            namespace=automate.Namespace.make_path("Cloud", "VM", "Provisioning", "StateMachines",
                parent=automate.Domain(name="ManageIQ (Locked)")))

        method = automate.Method(name=method, cls=ocls)
        method = method.copy_to(domain)
