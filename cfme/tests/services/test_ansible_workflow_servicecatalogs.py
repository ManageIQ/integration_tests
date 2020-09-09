import pytest

from cfme import test_requirements
from cfme.infrastructure.config_management.ansible_tower import AnsibleTowerProvider
from cfme.services.myservice import MyService
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.version import Version


pytestmark = [
    test_requirements.service,
    test_requirements.tower,
    pytest.mark.tier(2),
    pytest.mark.provider([AnsibleTowerProvider], scope='module'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.parametrize('ansible_api_version', ['v1', 'v2']),
    pytest.mark.ignore_stream('upstream')
]


@pytest.fixture(scope="function")
def ansible_workflow_catitem(appliance, provider, dialog, catalog, workflow_type):
    config_manager_obj = provider
    provider_name = config_manager_obj.data.get('name')
    try:
        template = config_manager_obj.data['provisioning_data'][workflow_type]
    except KeyError:
        pytest.skip(f"No such Ansible template: {workflow_type} found in cfme_data.yaml")
    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.ANSIBLE_TOWER,
        name=dialog.label,
        description="my catalog",
        display_in=True,
        catalog=catalog,
        dialog=dialog,
        provider=f'{provider_name} Automation Manager',
        config_template=template)
    yield catalog_item
    catalog_item.delete_if_exists()


def versioncheck(provider: AnsibleTowerProvider, ansible_api_version):
    return provider.version >= Version(3.6) and ansible_api_version == 'v1'


@pytest.mark.uncollectif(versioncheck, reason='API V1 not supported since Tower 3.6.')
@pytest.mark.parametrize('workflow_type', ['multiple_job_workflow', 'inventory_sync_workflow'],
        ids=['multiple_job_workflow', 'inventory_sync_workflow'], scope='module')
@pytest.mark.meta(automates=[BZ(1719051)])
def test_tower_workflow_item(appliance, ansible_workflow_catitem, workflow_type,
        ansible_api_version_change):
    """Tests ordering of catalog items for Ansible Workflow templates
    Metadata:
        test_flag: provision

    Polarion:
        assignee: jhenner
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
    msg = f'Request failed with the message {order_request.row.last_message.text}'
    assert order_request.is_succeeded(method='ui'), msg
    appliance.user.my_settings.default_views.set_default_view(
        'Configuration Management Providers',
        'List View'
    )


@pytest.mark.uncollectif(versioncheck, reason='API V1 not supported since Tower 3.6.')
@pytest.mark.parametrize('workflow_type', ['multiple_job_workflow'], ids=['multiple_job_workflow'])
def test_retire_ansible_workflow(appliance, ansible_workflow_catitem, workflow_type,
        ansible_api_version_change):
    """Tests retiring of catalog items for Ansible Workflow templates
    Metadata:
        test_flag: provision

    Polarion:
        assignee: jhenner
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/4h
    """
    service_catalogs = ServiceCatalogs(appliance, ansible_workflow_catitem.catalog,
        ansible_workflow_catitem.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', ansible_workflow_catitem.name)
    cells = {'Description': ansible_workflow_catitem.name}
    order_request = appliance.collections.requests.instantiate(cells=cells, partial_check=True)
    order_request.wait_for_request(method='ui')
    msg = f"Request failed with the message {order_request.row.last_message.text}"
    assert order_request.is_succeeded(method='ui'), msg
    myservice = MyService(appliance, ansible_workflow_catitem.name)
    myservice.retire()
