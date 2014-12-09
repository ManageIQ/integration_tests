import pytest

from utils.conf import cfme_data
from cfme.infrastructure.pxe import get_pxe_server_from_config, get_template_from_config
from cfme.provisioning import cleanup_vm, do_vm_provisioning
from utils import testgen
from utils.providers import setup_provider
from utils.randomness import generate_random_string

pytestmark = [
    pytest.mark.fixtureconf(server_roles="+automate +notifier"),
    pytest.mark.usefixtures('server_roles', 'uses_infra_providers')
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc, 'provisioning')
    pargnames, pargvalues, pidlist = testgen.pxe_servers(metafunc)
    argnames = argnames + ['pxe_server', 'pxe_cust_template']
    pxe_server_names = [pval[0] for pval in pargvalues]

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
        if not {'pxe_template', 'host', 'datastore',
                'pxe_server', 'pxe_image', 'pxe_kickstart',
                'pxe_root_password',
                'pxe_image_type', 'vlan'}.issubset(args['provisioning'].viewkeys()):
            # Need all  for template provisioning
            continue

        pxe_server_name = args['provisioning']['pxe_server']
        if pxe_server_name not in pxe_server_names:
            continue

        pxe_cust_template = args['provisioning']['pxe_kickstart']
        if pxe_cust_template not in cfme_data['customization_templates'].keys():
            continue

        argvalues[i].append(get_pxe_server_from_config(pxe_server_name))
        argvalues[i].append(get_template_from_config(pxe_cust_template))
        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="module")
def setup_pxe_servers_vm_prov(pxe_server, pxe_cust_template, provisioning):
    if not pxe_server.exists():
        pxe_server.create()
    pxe_server.set_pxe_image_type(provisioning['pxe_image'], provisioning['pxe_image_type'])
    if not pxe_cust_template.exists():
        pxe_cust_template.create()


@pytest.fixture()
def provider_init(provider_key):
    try:
        setup_provider(provider_key)
    except Exception:
        pytest.skip("It's not possible to set up this provider, therefore skipping")


@pytest.fixture(scope="function")
def vm_name():
    vm_name = 'test_pxe_prov_%s' % generate_random_string()
    return vm_name


@pytest.mark.usefixtures('setup_pxe_servers_vm_prov')
def test_pxe_provision_from_template(provider_key, provider_crud, provider_type, provider_mgmt,
                                     provisioning, vm_name, smtp_test, provider_init, request):

    # generate_tests makes sure these have values
    pxe_template, host, datastore, pxe_server, pxe_image, pxe_kickstart,\
        pxe_root_password, pxe_image_type, pxe_vlan = map(provisioning.get, ('pxe_template', 'host',
                                'datastore', 'pxe_server', 'pxe_image', 'pxe_kickstart',
                                'pxe_root_password', 'pxe_image_type', 'vlan'))

    request.addfinalizer(lambda: cleanup_vm(vm_name, provider_key, provider_mgmt))

    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]},
        'provision_type': 'PXE',
        'pxe_server': pxe_server,
        'pxe_image': {'name': [pxe_image]},
        'custom_template': {'name': [pxe_kickstart]},
        'root_password': pxe_root_password,
        'vlan': pxe_vlan,
    }

    do_vm_provisioning(pxe_template, provider_crud, vm_name, provisioning_data, request,
                       provider_mgmt, provider_key, smtp_test, num_sec=2100)
