import pytest

from cfme.services.catalogs import ec2_catalog_item as ec2
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from utils import error, testgen
from utils.randomness import generate_random_string
from utils.providers import setup_cloud_providers


pytestmark = [
    pytest.mark.usefixtures("logged_in"),
    pytest.mark.fixtureconf(server_roles="+automate"),
    pytest.mark.usefixtures('server_roles', 'setup_providers')
]

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
def dialog():
    dialog = "dialog_" + generate_random_string()
    service_dialog = ServiceDialog(label=dialog, description="my dialog",
                     submit=True, cancel=True)
    service_dialog.create()
    yield dialog


@pytest.yield_fixture(scope="function")
def catalog():
    cat_name = "cat_" + generate_random_string()
    catalog = Catalog(name=cat_name,
                  description="my catalog")
    catalog.create()
    yield catalog

@pytest.mark.usefixtures('setup_providers')
def test_ec2_catalog_item(provider_mgmt, provider_crud, provider_type, provisioning, dialog, catalog):
    # tries to delete the VM that gets created here
    vm_name = 'service_catalog_%s' % generate_random_string()
    image = provisioning['image']['name']
    item_name = generate_random_string()

    ec2_catalog_item = ec2.Instance(
        item_type="Amazon",
        item_name=item_name,
        description="my catalog",
        display_in=True,
        catalog=catalog.name,
        dialog=dialog,
        catalog_name=image,
        vm_name=vm_name,
        instance_type=provisioning['instance_type'],
        availability_zone=provisioning['availability_zone'],
        security_groups=[provisioning['security_group']],
        provider_mgmt=provider_mgmt,
        provider=provider_crud.name,
        guest_keypair="shared")

    ec2_catalog_item.create()

