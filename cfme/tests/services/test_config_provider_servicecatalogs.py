import pytest

from cfme import test_requirements
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.services.myservice import MyService

from cfme.utils import testgen
from cfme.utils.log import logger

pytestmark = [
    test_requirements.service,
    pytest.mark.tier(2),
    pytest.mark.meta(blockers=[1491704])]


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


@pytest.fixture
def config_manager(config_manager_obj):
    """ Fixture that provides a random config manager and sets it up"""
    if config_manager_obj.type == "Ansible Tower":
        config_manager_obj.create(validate=True)
    else:
        config_manager_obj.create()
    yield config_manager_obj
    config_manager_obj.delete()


@pytest.fixture(scope="function")
def catalog_item(appliance, request, config_manager, dialog, catalog):
    config_manager_obj = config_manager
    provider_name = config_manager_obj.yaml_data.get('name')
    provisioning_data = config_manager_obj.yaml_data['provisioning_data']
    item_type, provider_type, template = map(provisioning_data.get,
                                            ('item_type', 'provider_type', 'template'))

    catalog_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.ANSIBLE_TOWER,
        name=dialog.label,
        description="my catalog",
        display_in=True,
        catalog=catalog,
        dialog=dialog,
        provider='{} Automation Manager'.format(provider_name),
        config_template=template)
    request.addfinalizer(catalog_item.delete)
    return catalog_item


@pytest.mark.tier(2)
@pytest.mark.ignore_stream('upstream')
def test_order_tower_catalog_item(appliance, catalog_item, request):
    """Tests order catalog item
    Metadata:
        test_flag: provision
    """
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


@pytest.mark.tier(2)
@pytest.mark.ignore_stream('upstream')
def test_retire_ansible_service(appliance, catalog_item, request):
    """Tests order catalog item
    Metadata:
        test_flag: provision
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


@pytest.mark.tier(2)
@pytest.mark.ignore_stream('upstream')
def test_order_tower_catalog_item_jobs(appliance, catalog_item, request):
    """Tests order Ansible Tower catalog item and check status on Jobs page

    Metadata:
        test_flag: provision
    """
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    cells = {'Description': catalog_item.name}

    order_request = appliance.collections.requests.instantiate(cells=cells, partial_check=True)
    order_request.wait_for_request(method='ui')
    msg = "Ansible Tower Job failed"
    assert appliance.collections.ansible_tower_jobs.is_finished(), msg
