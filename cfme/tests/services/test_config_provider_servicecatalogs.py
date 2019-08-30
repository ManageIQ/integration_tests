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
    pytest.mark.uncollectif(lambda appliance,
        job_type: appliance.version < '5.10' and job_type == 'workflow')]


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
