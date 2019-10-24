# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils import testgen
from cfme.utils.blockers import BZ
from cfme.utils.blockers import GH
from cfme.utils.log import logger


pytestmark = [
    test_requirements.service,
    pytest.mark.tier(2),
    pytest.mark.parametrize('job_type', ['template', 'template_limit', 'template_survey',
        'textarea_survey'],
        ids=['template_job', 'template_limit_job', 'template_survey_job', 'textarea_survey_job'],
        scope='module'),
    pytest.mark.ignore_stream('upstream'),
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.config_managers(metafunc)
    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(list(zip(argnames, argvalue_tuple)))

        if not args['config_manager_obj'].yaml_data['provisioning']:
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope='module')


@pytest.fixture(scope="module")
def config_manager(config_manager_obj):
    """ Fixture that provides a random config manager and sets it up"""
    if config_manager_obj.type == "Ansible Tower":
        config_manager_obj.create(validate=True)
    else:
        config_manager_obj.create()
    yield config_manager_obj
    config_manager_obj.delete()


@pytest.fixture(scope="function")
def catalog_item(appliance, request, config_manager, ansible_tower_dialog, catalog, job_type):
    config_manager_obj = config_manager
    provider_name = config_manager_obj.yaml_data.get('name')
    template = config_manager_obj.yaml_data['provisioning_data'][job_type]
    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.ANSIBLE_TOWER,
        name=ansible_tower_dialog.label,
        description="my catalog",
        display_in=True,
        catalog=catalog,
        dialog=ansible_tower_dialog,
        provider='{} Automation Manager'.format(provider_name),
        config_template=template)
    request.addfinalizer(catalog_item.delete)
    return catalog_item


@pytest.mark.meta(automates=[BZ(1717500)])
# The 'textarea_survey' job type automates BZ 1717500
def test_order_tower_catalog_item(appliance, config_manager, catalog_item, request, job_type):
    """Tests ordering of catalog items for Ansible Template and Workflow jobs
    Metadata:
        test_flag: provision

    Bugzilla:
        1717500

    Polarion:
        assignee: nachandr
        initialEstimate: 1/4h
        casecomponent: Services
        caseimportance: high
    """
    if job_type == 'template_limit':
        host = config_manager.yaml_data['provisioning_data']['inventory_host']
        dialog_values = {'limit': host}
        service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name,
            dialog_values=dialog_values)
    else:
        service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)

    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    cells = {'Description': catalog_item.name}
    order_request = appliance.collections.requests.instantiate(cells=cells, partial_check=True)
    order_request.wait_for_request(method='ui')
    msg = 'Request failed with the message {}'.format(order_request.row.last_message.text)
    assert order_request.is_succeeded(method='ui'), msg
    appliance.user.my_settings.default_views.set_default_view('Configuration Management Providers',
                                                              'List View')


@pytest.mark.meta(blockers=[GH('ManageIQ/integration_tests:8610')])
def test_retire_ansible_service(appliance, catalog_item, request, job_type):
    """Tests retiring of catalog items for Ansible Template and Workflow jobs
    Metadata:
        test_flag: provision

    Polarion:
        assignee: nachandr
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/4h
    """
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    cells = {'Description': catalog_item.name}
    order_request = appliance.collections.requests.instantiate(cells=cells, partial_check=True)
    order_request.wait_for_request(method='ui')
    msg = "Request failed with the message {}".format(order_request.row.last_message.text)
    assert order_request.is_succeeded(method='ui'), msg
    myservice = MyService(appliance, catalog_item.name)
    myservice.retire()


@pytest.mark.manual
@test_requirements.tower
@pytest.mark.tier(1)
def test_config_manager_override_extra_vars_dialog_vsphere():
    """
    1. add tower 2.4.3 provider and perform refresh
    2. Go to job templates
    3. Create service dialog from third_job_template
    - this template is bound to vsphere55 inventory
    - simple_play_4_dockers.yaml playbook is part of this template
    - this playbook will touch /var/tmp/touch_from_play.txt
    - into /var/tmp/touch_from_play_dumped_vars.txt all variables
    available during play run will be dumped
    - this includes also variables passed from Tower or CFME
    - this project is linked with Tower and Vsphere55 credentials
    - Vsphere55 credentials are used when inventory is retrieved
    - Tower credentials are the creds used to login into VM which will be
    deployed
    - Vsphere template used for VM deployment must have ssh key "baked" in
      Prompt for Extra variables must be enabled.
    4. Add Vsphere55 provider into CFME and perform refresh
    5. Create new Catalog
    6. Add new catalog item for Vsphere vcentre - VMWare
    7. Give it name, display in catalog, catalog,
    8. Provisioning entry point:
    /Service/Provisioning/StateMachines/ServiceProvision_Template/CatalogI
    temInitialization
    Request info tab:
    - Name of template: template_Fedora-Cloud-Base-23-vm-tools_v4 (this
    template has ssh key which matches with Tower creentials)
    - VM Name: test_tower_pakotvan_1234 (it must start with test_tower_ -
    inventory script on Tower 2.4.3 was modified to look only for such VMs
    in order to speed up provisioning)
    Envirnment tab:
    - select where VM will be placed and datastore
    Hardware: Select at least 1GB ram for our template
    Network:
    vLAN: VM Network
    9. Automate -> Explorer
    10. Add new Domain
    11. Copy instance Infrastructure->Vm->Provisioning->StateMachines->VMP
    rovision_VM->Provision_VM
    from Template into your domain
    12. Edit this instance
    13. look for PostProvision in the first field/column
    14. Into Value column add:
    /ConfigurationManagement/AnsibleTower/Operations/StateMachines/Job/def
    ault?job_template_name=third_job_template
    15. Automate -> Customization -> Service dialogs -> tower_dialog
    Edit this dialog
    Extra variables:
    - make elements in extra variables writable (uncheck readonly).
    - add new element add 1 extra variable - variables must start with
    param_prefix, otherwised will be ignored!!!
    16. Order service
    Into limit field put exact name of your VM:  test_tower_pakotvan_1234
    17. Login to provision VM and `cat
    /var/tmp/touch_from_play_dumped_vars.txt` and grep for variables which
    were passed from CFME UI.

    Polarion:
        assignee: nachandr
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1d
        startsin: 5.7
    """
    pass
