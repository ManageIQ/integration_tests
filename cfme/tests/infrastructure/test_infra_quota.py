# -*- coding: utf-8 -*-
import fauxfactory
import pytest

import cfme.configure.access_control as ac
from cfme import test_requirements
from cfme.configure.access_control import Tenant
from cfme.fixtures import pytest_selenium as sel
from cfme.automate import explorer as automate
from cfme.provisioning import provisioning_form
from cfme.services import requests
from cfme.web_ui import fill, flash
from utils import testgen, version
from utils.wait import wait_for

pytestmark = [
    test_requirements.quota,
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('uses_infra_providers')
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['virtualcenter'])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope='module')


@pytest.fixture(scope="function")
def vm_name():
    vm_name = 'test_quota_prov_{}'.format(fauxfactory.gen_alphanumeric())
    return vm_name


@pytest.fixture(scope="module")
def domain(request):
    domain = automate.Domain(name=fauxfactory.gen_alphanumeric(), enabled=True)
    domain.create()
    request.addfinalizer(lambda: domain.delete() if domain.exists() else None)
    return domain


@pytest.fixture(scope="module")
def cls(request, domain):
    tcls = automate.Class(name="ProvisionRequestQuotaVerification",
        namespace=automate.Namespace.make_path("Infrastructure", "VM",
            "Provisioning", "StateMachines",
            parent=domain, create_on_init=True))
    tcls.create()
    request.addfinalizer(lambda: tcls.delete() if tcls.exists() else None)
    return tcls


@pytest.fixture(scope="module")
def copy_methods(domain):
    methods = ['rejected', 'validate_quotas']
    for method in methods:
        ocls = automate.Class(name="ProvisionRequestQuotaVerification",
            namespace=automate.Namespace.make_path("Infrastructure", "VM",
                "Provisioning", "StateMachines",
                parent=automate.Domain(name="ManageIQ (Locked)")))

        method = automate.Method(name=method, cls=ocls)

        method = method.copy_to(domain)


@pytest.fixture(scope="module")
def set_domain_priority(domain):
    automate.set_domain_order(domain.name)


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


@pytest.fixture(scope="function")
def prov_data(provider, provisioning):
    return {
        "first_name": fauxfactory.gen_alphanumeric(),
        "last_name": fauxfactory.gen_alphanumeric(),
        "email": "{}@{}.test".format(
            fauxfactory.gen_alphanumeric(), fauxfactory.gen_alphanumeric()),
        "manager_name": "{} {}".format(
            fauxfactory.gen_alphanumeric(), fauxfactory.gen_alphanumeric()),
        "vlan": provisioning.get("vlan", None),
        "datastore_name": {"name": provisioning["datastore"]},
        "host_name": {"name": provisioning["host"]},
        "provision_type": "Native Clone" if provider.type == "rhevm" else "VMware"
    }


@pytest.fixture(scope="function")
def template_name(provisioning):
    return provisioning["template"]


@pytest.fixture(scope="function")
def provisioner(request, setup_provider, provider):
    def _provisioner(template, provisioning_data, delayed=None):
        sel.force_navigate('infrastructure_provision_vms', context={
            'provider': provider,
            'template_name': template,
        })

        fill(provisioning_form, provisioning_data, action=provisioning_form.submit_button)
        flash.assert_no_errors()

    return _provisioner


@pytest.mark.uncollectif(lambda: version.current_version() >= '5.5')
def test_group_quota_max_memory_check_by_tagging(
        provisioner, prov_data, template_name, provider, request, vm_name, set_group_memory, bug):

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
    row_description = 'Provision from [{}] to [{}]'.format(template_name, vm_name)
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
                    fail_func=requests.reload, num_sec=300, delay=20)
    if version.current_version() >= "5.4":
        assert row.last_message.text == 'Request denied due to the following quota limits:'\
            '(Group Allocated Memory 0.00GB + Requested 4.00GB > Quota 2.00GB)'
    else:
        assert row.last_message.text == 'Request denied due to the following quota limits:'\
            '(Group Allocated Memory 0.00GB + Requested 4.00GB \> Quota 2.00GB)'


@pytest.mark.uncollectif(lambda: version.current_version() >= '5.5')
def test_group_quota_max_cpu_check_by_tagging(
        provisioner, prov_data, template_name, provider, request, vm_name, set_group_cpu, bug):

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
    row_description = 'Provision from [{}] to [{}]'.format(template_name, vm_name)
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells],
                    fail_func=sel.refresh, num_sec=300, delay=20)
    if version.current_version() >= "5.4":
        assert row.last_message.text == 'Request denied due to the following quota limits:'\
            '(Group Allocated vCPUs 0 + Requested 8 > Quota 2)'
    else:
        assert row.last_message.text == 'Request denied due to the following quota limits:'\
            '(Group Allocated vCPUs 0 + Requested 8 \> Quota 2)'


@pytest.mark.tier(1)
@pytest.mark.meta(blockers=[1367290])
def test_tenant_quota_max_cpu_check(
        provisioner, prov_data, template_name, provider, request, vm_name, bug):
    """ Test Tenant Quota-Max CPU by UI.

    Prerequisities:
        * A provider set up, supporting provisioning in CFME

    Steps:
        * Set the tenant quota for cpu by UI emforcement
        * Open the provisioning dialog.
        * Apart from the usual provisioning settings, set CPU greater then tenant quota cpu.
        * Submit the provisioning request and wait for it to finish.
        * Visit the requests page. The last message should state quota validation message.

    Metadata:
        test_flag: provision
    """
    cpu_data = {'cpu_cb': True, 'cpu': 2}
    roottenant = Tenant.get_root_tenant()
    roottenant.set_quota(**cpu_data)
    note = ('template {} to vm {} on provider {}'.format(template_name, vm_name, provider.key))
    prov_data["vm_name"] = vm_name
    prov_data["num_sockets"] = "8"
    prov_data["notes"] = note

    provisioner(template_name, prov_data)

    # nav to requests page to check quota validation
    row_description = 'Provision from [{}] to [{}]'.format(template_name, vm_name)
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells],
                    fail_func=sel.refresh, num_sec=500, delay=20)
    # BUG - https://bugzilla.redhat.com/show_bug.cgi?id=1364381
    # TODO: update assert message once the above bug is fixed.
    # assert row.last_message.text == 'Request exceeds maximum allowed for the following: \
    # (cpu - Used: 526 plus requested: 8 exceeds quota: 3))'
    assert row.reason.text == "Quota Exceeded"
