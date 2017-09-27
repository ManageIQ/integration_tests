# -*- coding: utf-8 -*-
import fauxfactory
import pytest

import cfme.configure.access_control as ac
from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.provisioning import do_vm_provisioning
from cfme.utils import testgen, version

pytestmark = [
    test_requirements.quota,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers')
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [VMwareProvider])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope='module')


@pytest.fixture(scope="function")
def vm_name():
    vm_name = 'test_quota_prov_{}'.format(fauxfactory.gen_alphanumeric())
    return vm_name


@pytest.yield_fixture(scope="module")
def set_group_memory():
    group = ac.Group(description='EvmGroup-super_administrator')
    group.edit_tags("Quota - Max Memory *", '2GB')
    yield
    group.remove_tag("Quota - Max Memory *", "2GB")


@pytest.yield_fixture(scope="module")
def set_group_cpu():
    group = ac.Group(description='EvmGroup-super_administrator')
    group.edit_tags("Quota - Max CPUs *", '2')
    yield
    group.remove_tag("Quota - Max CPUs *", "2")


@pytest.fixture(scope="module")
def roottenant(appliance):
    return appliance.collections.tenants.get_root_tenant()


@pytest.yield_fixture(scope="module")
def set_tenant_cpu(roottenant):
    cpu_data = {'cpu_cb': True, 'cpu': 2}
    reset_cpu_data = {'cpu_cb': False}
    roottenant.set_quota(**cpu_data)
    yield
    roottenant.set_quota(**reset_cpu_data)


@pytest.yield_fixture(scope="module")
def set_tenant_memory(roottenant):
    memory_data = {'memory_cb': True, 'memory': 2}
    reset_memory_data = {'memory_cb': False}
    roottenant.set_quota(**memory_data)
    yield
    roottenant.set_quota(**reset_memory_data)


@pytest.yield_fixture(scope="module")
def set_tenant_storage(roottenant):
    storage_data = {'storage_cb': True, 'storage': 0.01}
    reset_storage_data = {'storage_cb': False}
    roottenant.set_quota(**storage_data)
    yield
    roottenant.set_quota(**reset_storage_data)


@pytest.yield_fixture(scope="module")
def set_tenant_vm(roottenant):
    vm_data = {'vm_cb': True, 'vm': 1}
    reset_vm_data = {'vm_cb': False}
    roottenant.set_quota(**vm_data)
    yield
    roottenant.set_quota(**reset_vm_data)


@pytest.fixture(scope="function")
def prov_data(provider, provisioning):
    return {
        "first_name": fauxfactory.gen_alphanumeric(),
        "last_name": fauxfactory.gen_alphanumeric(),
        "email": "{}@{}.test".format(
            fauxfactory.gen_alphanumeric(), fauxfactory.gen_alphanumeric()),
        "manager_name": "{} {}".format(
            fauxfactory.gen_alphanumeric(), fauxfactory.gen_alphanumeric()),
        "vlan": provisioning.get("vlan"),
        "datastore_name": {"name": provisioning["datastore"]},
        "host_name": {"name": provisioning["host"]},
        "provision_type": "Native Clone" if provider.type == "rhevm" else "VMware"
    }


@pytest.fixture(scope="function")
def template_name(provisioning):
    return provisioning["template"]


@pytest.fixture(scope="function")
def provisioner(request, setup_provider, provider):
    def _provisioner(appliance, template, provisioning_data, vm_name, delayed=None):
        do_vm_provisioning(appliance, template_name=template, provider=provider, vm_name=vm_name,
                           provisioning_data=provisioning_data, request=None, smtp_test=None,
                           wait=False)
    return _provisioner


@pytest.mark.uncollectif(lambda: version.current_version() >= '5.5')
def test_group_quota_max_memory_check_by_tagging(appliance, provisioner, prov_data, template_name,
                                                 provider, request, vm_name, set_group_memory, bug):

    """ Test group Quota-Max Memory by tagging.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Set the group quota for memory by tagging
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set RAM greater then group quota memory.
        * Submit the provisioning request and wait for it to finish.
        * Visit the requests page. The last message should state quota validation message.

    Metadata:
        test_flag: provision
    """
    note = ('template {} to vm {} on provider {}'.format(template_name, vm_name, provider.key))
    prov_data["vm_name"] = vm_name
    prov_data["memory"] = "4096"
    prov_data["notes"] = note

    provisioner(template_name, prov_data)

    # nav to requests page to check quota validation
    request_description = 'Provision from [{}] to [{}]'.format(template_name, vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.last_message.text == \
        'Request denied due to the following quota limits:(Group Allocated Memory 0.00GB + ' \
        'Requested 4.00GB > Quota 2.00GB)'


@pytest.mark.uncollectif(lambda: version.current_version() >= '5.5')
def test_group_quota_max_cpu_check_by_tagging(appliance, provisioner, prov_data, template_name,
                                              provider, request, vm_name, set_group_cpu, bug):

    """ Test group Quota-Max CPU by tagging.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Set the group quota for cpu by tagging
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set CPU greater then group quota cpu.
        * Submit the provisioning request and wait for it to finish.
        * Visit the requests page. The last message should state quota validation message.

    Metadata:
        test_flag: provision
    """
    note = ('template {} to vm {} on provider {}'.format(template_name, vm_name, provider.key))
    prov_data["vm_name"] = vm_name
    prov_data["num_sockets"] = "8"
    prov_data["notes"] = note

    provisioner(template_name, prov_data)

    # nav to requests page to check quota validation
    request_description = 'Provision from [{}] to [{}]'.format(template_name, vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.last_message.text == \
        'Request denied due to the following quota limits:' \
        '(Group Allocated vCPUs 0 + Requested 8 > Quota 2)'


@pytest.mark.tier(2)
def test_tenant_quota_max_cpu_check(appliance, provisioner, prov_data, template_name, provider,
                                    request, vm_name, set_tenant_cpu, bug):
    """Test Tenant Quota-Max CPU by UI.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Set the tenant quota for cpu by UI enforcement
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set CPU greater then tenant quota cpu.
        * Submit the provisioning request and wait for it to finish.
        * Visit the requests page. The last message should state quota validation message.

    Metadata:
        test_flag: provision
    """
    prov_data = {
        'catalog': {
            'vm_name': vm_name
        },
        'environment': {
            'automatic_placement': True
        },
        'hardware': {
            'num_sockets': '8'
        }
    }

    provisioner(appliance, template_name, prov_data, vm_name)

    # nav to requests page to check quota validation
    request_description = 'Provision from [{}] to [{}]'.format(template_name, vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    # BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1364381
    # TODO: update assert message once the above bug is fixed.
    # assert row.last_message.text == 'Request exceeds maximum allowed for the following: \
    # (cpu - Used: 526 plus requested: 8 exceeds quota: 3))'
    assert provision_request.row.reason.text == "Quota Exceeded"


@pytest.mark.tier(2)
def test_tenant_quota_max_memory_check(appliance, provisioner, prov_data, template_name,
                                       provider, request, vm_name, set_tenant_memory, bug):
    """Test Tenant Quota-Max Memory by UI.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Set the tenant quota for memory by UI enforcement
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set memory greater then tenant quota memory.
        * Submit the provisioning request and wait for it to finish.
        * Visit the requests page. The last message should state quota validation message.

    Metadata:
        test_flag: provision
    """
    prov_data = {
        'catalog': {
            'vm_name': vm_name
        },
        'environment': {
            'automatic_placement': True
        },
        'hardware': {
            'memory': '4096'
        }
    }

    provisioner(appliance, template_name, prov_data, vm_name)

    # nav to requests page to check quota validation
    request_description = 'Provision from [{}] to [{}]'.format(template_name, vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.reason.text == "Quota Exceeded"


@pytest.mark.tier(2)
def test_tenant_quota_max_storage_check(appliance, provisioner, prov_data, template_name,
                                        provider, request, vm_name, set_tenant_storage, bug):
    """Test Tenant Quota-Max Storage by UI.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Set the tenant quota for storage by UI enforcement
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set storage greater then tenant quota storage.
        * Submit the provisioning request and wait for it to finish.
        * Visit the requests page. The last message should state quota validation message.

    Metadata:
        test_flag: provision
    """
    prov_data = {
        'catalog': {
            'vm_name': vm_name
        },
        'environment': {
            'automatic_placement': True
        }
    }

    provisioner(appliance, template_name, prov_data, vm_name)

    # nav to requests page to check quota validation
    request_description = 'Provision from [{}] to [{}]'.format(template_name, vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.reason.text == "Quota Exceeded"


@pytest.mark.tier(2)
def test_tenant_quota_max_num_vms_check(appliance, provisioner, prov_data, template_name, provider,
                                        request, vm_name, set_tenant_vm, bug):
    """Test Tenant Quota-Max number of vms by UI.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Set the tenant quota for storage by UI enforcement
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set num of vms greater then tenant quota vm.
        * Submit the provisioning request.
        * Approve the request and wait for it to finish.
        * Visit the requests page. The last message should state quota validation message.

    Metadata:
        test_flag: provision
    """
    prov_data = {
        'catalog': {
            'vm_name': vm_name,
            'num_vms': '4'
        },
        'environment': {
            'automatic_placement': True
        }
    }

    provisioner(appliance, template_name, prov_data, vm_name)

    # nav to requests page to check quota validation
    request_description = 'Provision from [{}] to [{}###]'.format(template_name, vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.approve_request(method='ui', reason="Approved")
    provision_request.wait_for_request(method='ui')
    assert provision_request.row.reason.text == "Quota Exceeded"
