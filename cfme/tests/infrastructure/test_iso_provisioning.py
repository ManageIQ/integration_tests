# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from utils.conf import cfme_data
from cfme.infrastructure.pxe import get_template_from_config, ISODatastore
from cfme.provisioning import cleanup_vm, do_vm_provisioning
from utils import testgen
from utils.providers import setup_provider

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers')
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc, 'provisioning')
    argnames = argnames + ['iso_cust_template', 'iso_datastore']

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # No provisioning data available
            continue

        if args['provider_type'] == "scvmm":
            continue

        provider_data = cfme_data.get('management_systems', {})[
            argvalue_tuple[argnames.index('provider_key')]]
        if not provider_data.get('iso_datastore', False):
            continue

        # required keys should be a subset of the dict keys set
        if not {'iso_template', 'host', 'datastore',
                'iso_file', 'iso_kickstart',
                'iso_root_password',
                'iso_image_type', 'vlan'}.issubset(args['provisioning'].viewkeys()):
            # Need all  for template provisioning
            continue

        iso_cust_template = args['provisioning']['iso_kickstart']
        if iso_cust_template not in cfme_data.get('customization_templates', {}).keys():
            continue

        argvalues[i].append(get_template_from_config(iso_cust_template))
        argvalues[i].append(ISODatastore(provider_data['name']))
        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture
def provider_init(provider_key, iso_cust_template, provisioning, iso_datastore):
    try:
        setup_provider(provider_key)
    except Exception:
        pytest.skip("It's not possible to set up this provider, therefore skipping")

    if not iso_datastore.exists():
        iso_datastore.create()
    # Fails on upstream, BZ1109256
    iso_datastore.set_iso_image_type(provisioning['iso_file'], provisioning['iso_image_type'])
    if not iso_cust_template.exists():
        iso_cust_template.create()


@pytest.fixture(scope="function")
def vm_name():
    vm_name = 'test_iso_prov_%s' % fauxfactory.gen_alphanumeric(8)
    return vm_name


@pytest.mark.meta(blockers=[1200783, 1207209])
def test_iso_provision_from_template(provider_key, provider_crud, provider_type, provider_mgmt,
                                     provisioning, vm_name, smtp_test, provider_init, request):
    """Tests ISO provisioning

    Metadata:
        test_flag: iso, provision
        suite: infra_provisioning
    """
    # generate_tests makes sure these have values
    iso_template, host, datastore, iso_file, iso_kickstart,\
        iso_root_password, iso_image_type, vlan = map(provisioning.get, ('pxe_template', 'host',
                                'datastore', 'iso_file', 'iso_kickstart',
                                'iso_root_password', 'iso_image_type', 'vlan'))

    request.addfinalizer(lambda: cleanup_vm(vm_name, provider_key, provider_mgmt))

    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]},
        'provision_type': 'ISO',
        'iso_file': {'name': [iso_file]},
        'custom_template': {'name': [iso_kickstart]},
        'root_password': iso_root_password,
        'vlan': vlan,
    }

    do_vm_provisioning(iso_template, provider_crud, vm_name, provisioning_data, request,
                       provider_mgmt, provider_key, smtp_test, num_sec=1500)
