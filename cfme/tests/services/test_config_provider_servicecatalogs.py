import pytest

from cfme import test_requirements
from cfme.configure.settings import DefaultView
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.services.myservice import MyService
from cfme.services.catalogs.catalog_item import CatalogItem

from cfme.utils import testgen, version
from cfme.utils.log import logger


pytestmark = [
    test_requirements.service,
    pytest.mark.tier(2)]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.config_managers(metafunc)
    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        if not args["config_manager_obj"].yaml_data['provisioning']:
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.yield_fixture
def config_manager(config_manager_obj):
    """ Fixture that provides a random config manager and sets it up"""
    if config_manager_obj.type == "Ansible Tower":
        config_manager_obj.create(validate=True)
    else:
        config_manager_obj.create()
    yield config_manager_obj
    config_manager_obj.delete()


@pytest.fixture(scope="function")
def catalog_item(request, config_manager, dialog, catalog):
    config_manager_obj = config_manager
    provider_name = config_manager_obj.yaml_data.get('name')
    provisioning_data = config_manager_obj.yaml_data['provisioning_data']
    item_type, provider_type, template = map(provisioning_data.get,
                                            ('item_type', 'provider_type', 'template'))
    catalog_item = CatalogItem(item_type=item_type,
                               name=dialog.label,
                               description="my catalog",
                               display_in=True,
                               catalog=catalog,
                               dialog=dialog,
                               provider=version.pick({
                                   '5.7': '{} Configuration Manager'.format(provider_name),
                                   '5.8': '{} Automation Manager'.format(provider_name)}),
                               provider_type=provider_type,
                               config_template=template)
    request.addfinalizer(catalog_item.delete)
    return catalog_item


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_order_tower_catalog_item(appliance, catalog_item, request):
    """Tests order catalog item
    Metadata:
        test_flag: provision
    """
    catalog_item.create()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    cells = {'Description': catalog_item.name}
    order_request = appliance.collections.requests.instantiate(cells=cells, partial_check=True)
    order_request.wait_for_request(method='ui')
    assert order_request.is_succeeded(method='ui')
    DefaultView.set_default_view("Configuration Management Providers", "List View")


@pytest.mark.tier(2)
@pytest.mark.ignore_stream("upstream")
def test_retire_ansible_service(appliance, catalog_item, request):
    """Tests order catalog item
    Metadata:
        test_flag: provision
    """
    catalog_item.create()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    cells = {'Description': catalog_item.name}
    order_request = appliance.collections.requests.instantiate(cells=cells, partial_check=True)
    order_request.wait_for_request(method='ui')
    assert order_request.is_succeeded(method='ui')
    myservice = MyService(appliance, catalog_item.name)
    myservice.retire()
