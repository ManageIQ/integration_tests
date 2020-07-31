import pytest

from cfme import test_requirements
from cfme.infrastructure.config_management.ansible_tower import AnsibleTowerProvider
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.version import Version


pytestmark = [
    test_requirements.service,
    pytest.mark.provider([AnsibleTowerProvider], scope='module'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2),
    pytest.mark.parametrize('ansible_api_version', ['v1', 'v2']),
    pytest.mark.ignore_stream('upstream')
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
        provider=f'{provider_name} Automation Manager',
        config_template=template)
    request.addfinalizer(catalog_item.delete)
    return catalog_item


@pytest.mark.parametrize('job_type', ['template', 'template_limit', 'template_survey',
        'textarea_survey'],
        ids=['template_job', 'template_limit_job', 'template_survey_job', 'textarea_survey_job'],
        scope='module')
@pytest.mark.meta(automates=[BZ(1717500)])
# The 'textarea_survey' job type automates BZ 1717500
def test_order_tower_catalog_item(appliance, provider: AnsibleTowerProvider,
                                  catalog_item, request, job_type, ansible_api_version_change):
    """Tests ordering of catalog items for Ansible Template and Workflow jobs
    Metadata:
        test_flag: provision

    Bugzilla:
        1717500

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Services
        caseimportance: high
    """
    bug = BZ(1861827)
    if job_type == 'template_limit':
        host = provider.data['provisioning_data']['inventory_host']
        dialog_values = {'limit': host}
        service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name,
            dialog_values=dialog_values)
    elif (job_type == 'template_survey' and Version(provider.version) >= Version('3.5')
          and bug.blocks):
        pytest.skip(f'Blocked by {bug}')
    else:
        service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)

    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    cells = {'Description': catalog_item.name}
    order_request = appliance.collections.requests.instantiate(cells=cells, partial_check=True)
    order_request.wait_for_request(method='ui')
    msg = f'Request failed with the message {order_request.row.last_message.text}'
    assert order_request.is_succeeded(method='ui'), msg
    appliance.user.my_settings.default_views.set_default_view('Configuration Management Providers',
                                                              'List View')


@pytest.mark.parametrize('job_type', ['template'], ids=['template_job'])
def test_retire_ansible_service(appliance, catalog_item, request, job_type,
        ansible_api_version_change):
    """Tests retiring of catalog items for Ansible Template and Workflow jobs
    Metadata:
        test_flag: provision

    Polarion:
        assignee: jhenner
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
    msg = f"Request failed with the message {order_request.row.last_message.text}"
    assert order_request.is_succeeded(method='ui'), msg
    myservice = MyService(appliance, catalog_item.name)
    myservice.retire()


@pytest.mark.ignore_stream('5.10')
@pytest.mark.customer_scenario
@pytest.mark.meta(automates=[1740814])
@pytest.mark.parametrize('job_type', ['template'], ids=['template_job'])
def test_change_ansible_tower_job_template(catalog_item, job_type, ansible_api_version_change):
    """
    Bugzilla:
        1740814

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/16h
        startsin: 5.11
        testSteps:
            1. Add a Ansible Tower provider
            2. Add an Ansible Tower Catalog Item with 'Display in Catalog' Checked
            3. Edit the Catalog item, change the Tower job template
        expectedResults:
            1.
            2.
            3. 'Display in Catalog' remains checked after template change
    """
    view = navigate_to(catalog_item, 'Edit')

    # Change the Ansible Tower Template
    view.select_orch_template.fill("bz-survey")
    view.save.click()
    view = navigate_to(catalog_item, 'Edit')

    # "Display in Catalog" should be checked
    assert view.display.read()
    view.cancel.click()
