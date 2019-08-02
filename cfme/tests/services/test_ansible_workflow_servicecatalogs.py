# -*- coding: utf-8 -*-:
import pytest

from cfme import test_requirements
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils import testgen
from cfme.utils.blockers import BZ
from cfme.utils.log import logger


pytestmark = [
    test_requirements.service,
    pytest.mark.tier(2),
    pytest.mark.ignore_stream('upstream')
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.config_managers(metafunc)
    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        if not args['config_manager_obj'].yaml_data['provisioning']:
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope='module')


@pytest.fixture(scope="module")
def tower_manager(config_manager_obj):
    """ Fixture that sets up Ansible Tower"""
    if config_manager_obj.type == "Ansible Tower":
        config_manager_obj.create(validate=True)
    yield config_manager_obj
    config_manager_obj.delete()


@pytest.fixture(scope="function")
def ansible_workflow_catitem(appliance, request, tower_manager, dialog, catalog):
    job_type = 'workflow'
    config_manager_obj = tower_manager
    provider_name = config_manager_obj.yaml_data.get('name')
    try:
        if config_manager_obj.yaml_data['provisioning_data'][job_type]:
            template = config_manager_obj.yaml_data['provisioning_data'][job_type]
    except KeyError:
        pytest.skip("No such Ansible template: {} found in cfme_data.yaml".format(job_type))
    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.ANSIBLE_TOWER,
        name=dialog.label,
        description="my catalog",
        display_in=True,
        catalog=catalog,
        dialog=dialog,
        provider='{} Automation Manager'.format(provider_name),
        config_template=template)
    yield catalog_item
    catalog_item.delete_if_exists()


@pytest.mark.meta(automates=[BZ(1719051)])
def test_tower_workflow_item(appliance, tower_manager, ansible_workflow_catitem, request):
    """Tests ordering of catalog items for Ansible Workflow templates
    Metadata:
        test_flag: provision

    Polarion:
        assignee: nachandr
        initialEstimate: 1/4h
        casecomponent: Services
        caseimportance: high
    """
    service_catalogs = ServiceCatalogs(appliance, ansible_workflow_catitem.catalog,
        ansible_workflow_catitem.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', ansible_workflow_catitem.name)
    cells = {'Description': ansible_workflow_catitem.name}
    order_request = appliance.collections.requests.instantiate(cells=cells, partial_check=True)
    order_request.wait_for_request(method='ui')
    msg = 'Request failed with the message {}'.format(order_request.row.last_message.text)
    assert order_request.is_succeeded(method='ui'), msg
    appliance.user.my_settings.default_views.set_default_view(
        'Configuration Management Providers',
        'List View'
    )


def test_retire_ansible_workflow(appliance, ansible_workflow_catalog_item, request):
    """Tests retiring of catalog items for Ansible Workflow templates
    Metadata:
        test_flag: provision

    Polarion:
        assignee: nachandr
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/4h
    """
    service_catalogs = ServiceCatalogs(appliance, ansible_workflow_catitem.name.catalog,
        ansible_workflow_catitem.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', ansible_workflow_catitem.name)
    cells = {'Description': ansible_workflow_catitem.name}
    order_request = appliance.collections.requests.instantiate(cells=cells, partial_check=True)
    order_request.wait_for_request(method='ui')
    msg = "Request failed with the message {}".format(order_request.row.last_message.text)
    assert order_request.is_succeeded(method='ui'), msg
    myservice = MyService(appliance, ansible_workflow_catitem.name)
    myservice.retire()
