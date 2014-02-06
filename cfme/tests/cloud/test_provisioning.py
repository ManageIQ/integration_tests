import pytest

from cfme.cloud.provisioning import provisioning_form
from cfme.web_ui import tabstrip
from fixtures.mgmt_system import setup_cloud_providers
from utils import testgen
from utils.randomness import generate_random_string
from utils.log import logger
from utils.wait import wait_for

# pytest_generate_tests = testgen.parametrize(testgen.cloud_providers,
#     , scope="module")

# def pytest_generate_tests(metafunc):
#     argnames, argvalues, idlist = testgen.cloud_providers(metafunc, 'small_template', 'hosts')
#     # Filter out providers missing provisioning hosts
#     new_argvalues = []
#     new_idlist = []
#     for i, argvalue_tuple in enumerate(argvalues):
#         args = dict(zip(argnames, argvalue_tuple))
#         provisioning_hosts = filter(lambda d: d.get('test_provisioning'), args.get('hosts', {}))
#         if provisioning_hosts:
#             new_argvalues.append([args[argname] for argname in argnames])
#             new_idlist.append(idlist[i])
#     metafunc.parametrize(argnames, new_argnavlues, ids=new_idlist)

pytestmark = pytest.mark.fixtureconf(server_roles="+automate")


def pytest_generate_tests(metafunc):
    # Filter out providers without templates defined
    argnames, argvalues, idlist = testgen.cloud_providers(metafunc,
        'small_template', 'provisioning')
    new_argvalues = []
    new_idlist = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        try:
            args['small_template']['name']
        except (KeyError, TypeError):
            # KeyError: ['name'] is not defined on 'small_template' or
            # TypeError: 'small_template' is not a dict
            # Either way, move on to the next provider
            continue

        if not args['provisioning']:
            # Don't know what type of instance to provision, move on
            continue

        # Populate new idlist with matching provider
        new_idlist.append(idlist[i])
        # Populate argvalues with values in the original order
        new_argvalues.append([args[argname] for argname in argnames])
    metafunc.parametrize(argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="module")
def setup_providers():
    # Normally function-scoped
    setup_cloud_providers()


@pytest.yield_fixture(scope="function")
def vm_name(provider_crud):
    # Don't let the name fool you, it also tries to delete the VM that gets made with this name
    vm_name = generate_random_string()
    yield vm_name
    try:
        provider_mgmt = provider_crud.get_mgmt_system()
        provider_mgmt.delete_vm(vm_name)
        logger.info('Cleaned up VM %s' % vm_name)
    except:
        # The mgmt_sys classes raise Exception :\
        logger.error('Failed to clean up VM %s' % vm_name)


def test_provision_from_template(provider_crud, setup_providers, server_roles,
        vm_name, small_template, provisioning):
    # This is ensured to work by pytest_generate_tests
    template_name = small_template['name']

    pytest.sel.force_navigate('cloud_provision_instances', context={
        'provider_name': provider_crud.name,
        'template_name': template_name,
    })

    note = ('Testing provisioning from template %s to vm %s on provider %s' %
        (template_name, vm_name, provider_crud.key))
    provisioning_data = {
        'email': 'template_provisioner@example.com',
        'first_name': 'Template',
        'last_name': 'Provisioner',
        'notes': note,
        'instance_name': vm_name,
        'instance_type': provisioning['instance_type'],
        'availability_zone': provisioning['availability_zone'],
        #'security_groups': provisioning['security_group']
    }
    # Workaround :(
    tabstrip.select_tab('Environment')
    pytest.sel.click('//option[contains(text(), "%s")]' % provisioning['security_group'])
    provisioning_form.fill(provisioning_data)
    pytest.sel.click(provisioning_form.submit_button)
    mgmt = provider_crud.get_mgmt_system()
    # Wait for the VM to appear on the provider backend
    wait_for(mgmt.vm_status, vm_name, handle_exception=True)
