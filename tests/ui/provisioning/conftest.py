# -*- coding: utf-8 -*-
# pylint: disable=W0621
import pytest

@pytest.fixture
def provisioning_start_page(infra_vms_pg):
    '''Navigates to the page to start provisioning'''
    vm_pg = infra_vms_pg
    return vm_pg.click_on_provision_vms()

@pytest.fixture(scope="module", # IGNORE:E1101
               params=["linux_template_workflow",
               "rhevm_pxe_workflow"])
def provisioning_data(request, cfme_data):
    '''Returns all provisioning data'''
    param = request.param
    return cfme_data.data["provisioning"][param]

@pytest.fixture
def random_name(random_string):
    '''Returns random name addition for vms'''
    return '_%s' % random_string

@pytest.fixture(scope="module", # IGNORE:E1101
               params=["linux_template_workflow"])
def provisioning_data_basic_only(request, cfme_data):
    '''Returns only one set of provisioning data'''
    param = request.param
    return cfme_data.data["provisioning"][param]

@pytest.fixture
def enables_automation_engine(cnf_configuration_pg):
    '''Enables Automate Engine in Configure'''
    conf_pg = cnf_configuration_pg
    conf_pg.click_on_settings()
    return conf_pg.enable_automation_engine()
