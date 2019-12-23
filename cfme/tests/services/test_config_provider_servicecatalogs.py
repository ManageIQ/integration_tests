import pytest

from cfme import test_requirements
from cfme.infrastructure.config_management.ansible_tower import AnsibleTowerProvider
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.blockers import BZ
from cfme.utils.log import logger


pytestmark = [
    test_requirements.service,
    pytest.mark.provider([AnsibleTowerProvider], scope='module'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2),
    pytest.mark.parametrize('job_type', ['template', 'template_limit', 'template_survey',
        'textarea_survey', 'multiselect_survey'],
        ids=['template_job', 'template_limit_job', 'template_survey_job', 'textarea_survey_job',
             'multiselect_survey'],
        scope='module'),
    pytest.mark.ignore_stream('upstream'),
]


@pytest.fixture(scope="function")
def catalog_item(appliance, request, provider, ansible_tower_dialog, catalog, job_type):
    config_manager_obj = provider
    provider_name = config_manager_obj.data.get('name')
    template = config_manager_obj.data['provisioning_data'][job_type]
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
# The 'textarea_survey' job type automates BZ 1717500.
# The 'multiselect_survey' job type automates BZ 1761581.
def test_order_tower_catalog_item(appliance, provider, catalog_item, request, job_type):
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
        host = provider.data['provisioning_data']['inventory_host']
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
