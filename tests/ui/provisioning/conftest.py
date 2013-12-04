# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest


@pytest.fixture(
    scope="module",  # IGNORE:E1101
    params=["management_systems"])
def providers_data(request, cfme_data):
    '''Returns Management Systems data'''
    param = request.param
    return cfme_data.data[param]


@pytest.fixture
def provisioning_start_page(infra_vms_pg):
    '''Navigates to the page to start provisioning'''
    vm_pg = infra_vms_pg
    return vm_pg.click_on_provision_vms()


@pytest.fixture
def inst_provisioning_start_page(cloud_instances_pg):
    '''Navigates to page to start instance provisioning'''
    return cloud_instances_pg.click_on_provision_instances()


@pytest.fixture(
    scope="module",  # IGNORE:E1101
    params=["linux_template_workflow",
            "rhevm_pxe_workflow"])
def infra_provisioning_data(request, cfme_data):
    '''Returns all infrastructure provider provisioning data'''
    param = request.param
    return cfme_data.data["provisioning"][param]


@pytest.fixture(
    scope="module",  # IGNORE:E1101
    params=["rhevm_pxe_workflow"])
def pxe_provisioning_data(request, cfme_data):
    '''Returns data for RHEVM PXE Provisioning'''
    param = request.param
    return cfme_data.data["provisioning"][param]


@pytest.fixture(
    scope="module",  # IGNORE:E1101
    params=["ec2_image_workflow"])
def ec2_provisioning_data(request, cfme_data):
    '''Returns all ec2 provisioning data'''
    param = request.param
    return cfme_data.data["provisioning"][param]


@pytest.fixture(
    scope="module",  # IGNORE:E1101
    params=["openstack_image_workflow"])
def openstack_provisioning_data(request, cfme_data):
    '''Returns all openstack provisioning data'''
    param = request.param
    return cfme_data.data["provisioning"][param]


@pytest.fixture
def random_name(random_string):
    '''Returns random name addition for vms'''
    return '_%s' % random_string


@pytest.fixture(
    scope="module",  # IGNORE:E1101
    params=["linux_template_workflow"])
def provisioning_data_basic_only(request, cfme_data):
    '''Returns only one set of provisioning data'''
    param = request.param
    return cfme_data.data["provisioning"][param]


@pytest.fixture(
    scope="module",  # IGNORE:E1101
    params=["vmware_linux_workflow"])
def vmware_linux_setup_data(request, cfme_data):
    ''' Returns data for first VM for clone/retire tests'''
    param = request.param
    return cfme_data.data["clone_retire_setup"][param]


@pytest.fixture(
    scope="module",  # IGNORE:E1101
    params=["vmware_publish_to_template"])
def vmware_publish_to_template(request, cfme_data):
    '''Returns publish to template data'''
    param = request.param
    return cfme_data.data["provisioning"][param]


@pytest.fixture
def enables_automation_engine(cnf_configuration_pg):
    '''Enables Automate Engine in Configure'''
    conf_pg = cnf_configuration_pg
    conf_pg.click_on_settings()
    return conf_pg.enable_automation_engine()
