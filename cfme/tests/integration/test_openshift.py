# -*- coding: utf-8 -*-
"""This module tests provisioning of OpenShift service using prepared AE code in CFME."""
import fauxfactory
import pytest
from requests import get

from cfme.automate.simulation import simulate
from cfme.infrastructure.virtual_machines import Vm
from cfme.services import requests
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.catalogs.service_catalogs import order_catalog_item
from cfme.web_ui import Input
from cfme.web_ui.tabstrip import TabStripForm
from utils import conf, testgen
from utils.wait import wait_for, TimedOutError


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.ignore_stream("upstream", "5.2", "5.5"),  # TODO: 5.5 disabled due to RHEL7 there
    pytest.mark.meta(server_roles="+automate")]


order_form = TabStripForm(
    tab_fields={
        'Accounts': [
            ('os_password', Input("ose_password__protected")),
        ],
    }
)


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.infra_providers(metafunc,
        'openshift', 'provisioning', scope="module", template_location=["openshift", "template"])
    new_idlist = []
    new_argvalues = []
    basic_info = conf.cfme_data.basic_info
    if ("openshift_installer" in basic_info and "openshift_keys" in basic_info
            and "openshift_rhscl" in basic_info):
        new_idlist = idlist
        new_argvalues = argvalues

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="module")
def ose_tags_generated():
    simulate(
        instance="Request",
        message="create",
        request="osetags",
        attribute="<None>",
        execute_methods=True)


@pytest.fixture(scope="module")
def scl_ruby_present(request, ose_tags_generated, ssh_client_modscope):
    url = conf.cfme_data.basic_info.openshift_rhscl
    if ssh_client_modscope.run_command("ls /etc/yum.repos.d/ose-rhscl.repo").rc != 0:
        ssh_client_modscope.run_command("echo '[ose-rhscl]' > /etc/yum.repos.d/ose-rhscl.repo")
        ssh_client_modscope.run_command("echo 'name=ose-rhscl' >> /etc/yum.repos.d/ose-rhscl.repo")
        ssh_client_modscope.run_command(
            "echo 'baseurl={}' >> /etc/yum.repos.d/ose-rhscl.repo".format(url))
        ssh_client_modscope.run_command("echo 'enabled=1' >> /etc/yum.repos.d/ose-rhscl.repo")
        ssh_client_modscope.run_command("echo 'gpgcheck=0' >> /etc/yum.repos.d/ose-rhscl.repo")
    if ssh_client_modscope.run_command("rpm -qa | grep ruby193-ruby").rc != 0:
        ssh_client_modscope.run_command("yum -y install ruby193-ruby")

    @request.addfinalizer
    def _remove_scl():
        ssh_client_modscope.run_command("yum -y remove ruby193-ruby")
        ssh_client_modscope.run_command("rm -f /etc/yum.repos.d/ose-rhscl.repo")
        ssh_client_modscope.run_command("yum clean all")


@pytest.fixture(scope="module")
def installer_in_place(request, ssh_client_modscope, scl_ruby_present):
    url = conf.cfme_data.basic_info.openshift_installer
    request.addfinalizer(lambda: ssh_client_modscope.run_command("rm -rf /root/oo-install-ose"))
    r = ssh_client_modscope.run_command(
        "cd /root; wget -O installer.tar.gz {}; tar xf installer.tar.gz; rm -f installer.tar.gz"
        .format(url))
    assert r.rc == 0


@pytest.fixture(scope="module")
def keys_in_place(request, ssh_client_modscope, installer_in_place):
    url = conf.cfme_data.basic_info.openshift_keys
    r = ssh_client_modscope.run_command(
        "cd /root/.ssh; wget -O keys.tar.gz {}; tar xf keys.tar.gz; rm -f keys.tar.gz"
        .format(url))
    assert r.rc == 0
    ssh_client_modscope.run_command("mkdir -p /root/.ssh/backup")
    if ssh_client_modscope.run_command("test -e /root/.ssh/id_rsa").rc == 0:
        ssh_client_modscope.run_command("mv /root/.ssh/id_rsa /root/.ssh/backup/")
        request.addfinalizer(
            lambda: ssh_client_modscope.run_command(
                "mv /root/.ssh/backup/id_rsa /root/.ssh/id_rsa"))
    if ssh_client_modscope.run_command("test -e /root/.ssh/id_rsa.pub").rc == 0:
        ssh_client_modscope.run_command("mv /root/.ssh/id_rsa.pub /root/.ssh/backup/")
        request.addfinalizer(
            lambda: ssh_client_modscope.run_command(
                "mv /root/.ssh/backup/id_rsa.pub /root/.ssh/id_rsa.pub"))
    ssh_client_modscope.run_command("chown -R root.root /root/.ssh/id_rsa_ose*")
    ssh_client_modscope.run_command("mv /root/.ssh/id_rsa_ose /root/.ssh/id_rsa")
    ssh_client_modscope.run_command("mv /root/.ssh/id_rsa_ose.pub /root/.ssh/id_rsa.pub")


@pytest.fixture(scope="module")
def catalog(request, keys_in_place):
    catalog = Catalog(
        name="Openshift {}".format(fauxfactory.gen_alpha()),
        description="A description",
        items=None)
    catalog.create()
    request.addfinalizer(catalog.delete)
    return catalog


def test_openshift_catalog_item_all_in_one(
        provider, setup_provider_modscope, request, openshift, provisioning, catalog):
    """This test uses canned setup AE code to provision a RH OpenShift deployment using CFME."""
    vm_name = "test_ose_aio_{}".format(fauxfactory.gen_alpha())

    @request.addfinalizer
    def _cleanup_vms():
        for vm in [vm for vm in provider.mgmt.list_vm() if vm.startswith(vm_name)]:
            if provider.mgmt.does_vm_exist(vm):
                provider.mgmt.delete_vm(vm)
    prov_data = {"vm_name": vm_name, "address_mode": "dhcp"}
    prov_data["template"] = openshift["template"]
    prov_data["host_name"] = {"Name": provisioning["host"]}
    prov_data["datastore_name"] = {"Name": provisioning["datastore"]}
    if "provisioning_override" in openshift:
        prov_data.update(openshift["provisioning_override"])
    # TODO: Unify in YAML
    if "item_type" in provisioning:
        ci_type = provisioning.pop("item_type")
    elif "catalog_item_type" in provisioning:
        ci_type = provisioning.pop("catalog_item_type")
    else:
        pytest.fail("YAML does not have item type specified")

    if ci_type == "RHEV":
        prov_data['provision_type'] = 'Native Clone'

    catalog_name = prov_data.pop("template")  # Bad naming
    item = CatalogItem(
        name="OSE AIO {}".format(fauxfactory.gen_alpha()),
        catalog=catalog.name,
        description="A description",
        display_in=True,
        dialog="OSE Installer",
        domain="RedHat (Locked)",
        entry_point=[
            "Portfolio", "OpenShift", "Installer", "ServiceProvision_Template",
            "oseINSTALLER (oseINSTALLER)"],
        item_type=ci_type,
        provider=provider.name,
        catalog_name=catalog_name,
        prov_data=prov_data)
    item.create()
    request.addfinalizer(item.delete)
    item.edit_tags("OSE Policy", "Broker", "Node", "msgServer", "dbServer")

    password = fauxfactory.gen_alpha()

    order_catalog_item(item, {order_form: {"os_password": password}})

    def _check_the_service_vms():
        # We need to help RHEV refresh a bit
        vms = [vm for vm in provider.mgmt.list_vm() if vm.startswith(vm_name)]
        was_refresh = False
        for vm in vms:
            vm_crud_obj = Vm(vm, provider)
            if not vm_crud_obj.exists:
                if not was_refresh:
                    provider.refresh_provider_relationships()
                    was_refresh = True
            else:
                # Check power state, eventually refresh
                try:
                    vm_crud_obj.wait_for_vm_state_change(desired_state=Vm.STATE_ON, timeout=30)
                except TimedOutError:
                    if not was_refresh:
                        provider.refresh_provider_relationships()
                        was_refresh = True
        pytest.sel.force_navigate("services_requests")

    cells = {
        'Request Type': "Service Provision",
        'Description': "Provisioning Service [{iname}] from [{iname}]".format(iname=item.name)}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=_check_the_service_vms, num_sec=45 * 60, delay=20)

    # There should be only one machine with such name
    vms = [vm for vm in provider.mgmt.list_vm() if vm.startswith(vm_name)]
    assert len(vms) == 1
    # TODO: Check running Openshift
    vm = vms[0]
    ip = provider.mgmt.get_ip_address(vm)
    print ip, password

    try:
        print get("http://{}".format(ip))
        print "http ^^^"
    except:
        pass

    try:
        print get("https://{}".format(ip))
        print "https ^^^"
    except:
        pass
