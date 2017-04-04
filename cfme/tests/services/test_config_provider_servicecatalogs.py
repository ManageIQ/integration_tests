import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.service_dialogs import ServiceDialog
from cfme.configure.settings import DefaultView
from cfme.services import requests
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services.myservice import MyService
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.catalog_item import CatalogItem
from utils import testgen, version
from utils.wait import wait_for
from utils.blockers import BZ

pytestmark = [
    test_requirements.service,
    pytest.mark.ignore_stream("5.5"),
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
    DefaultView.set_default_view("Configuration Management Providers", "Grid View")
    if config_manager_obj.type == "Ansible Tower":
        config_manager_obj.create(validate=True)
    else:
        config_manager_obj.create()
    yield config_manager_obj
    config_manager_obj.delete()


@pytest.yield_fixture(scope="function")
def dialog(request):
    dialog_name = "dialog_" + fauxfactory.gen_alphanumeric()
    service_name = fauxfactory.gen_alphanumeric()
    element_data = dict(
        ele_label="ele_" + fauxfactory.gen_alphanumeric(),
        ele_name="service_name",
        ele_desc="my ele desc",
        choose_type="Text Box",
        default_text_box=service_name
    )
    service_dialog = ServiceDialog(label=dialog_name, description="my dialog",
                     submit=True, cancel=True,
                     tab_label="tab_" + fauxfactory.gen_alphanumeric(), tab_desc="my tab desc",
                     box_label="box_" + fauxfactory.gen_alphanumeric(), box_desc="my box desc")
    service_dialog.create(element_data)
    request.addfinalizer(service_dialog.delete)
    yield dialog_name, service_name


@pytest.yield_fixture(scope="function")
def catalog(request):
    catalog = "cat_" + fauxfactory.gen_alphanumeric()
    cat = Catalog(name=catalog,
                  description="my catalog")
    cat.create()
    request.addfinalizer(cat.delete)
    yield catalog


@pytest.fixture(scope="function")
def catalog_item(request, config_manager, dialog, catalog):
    dialog_name, service_name = dialog
    config_manager_obj = config_manager
    provisioning_data = config_manager_obj.yaml_data['provisioning_data']
    item_type, provider_type, provider, template = map(provisioning_data.get,
                                                       ('item_type',
                                                        'provider_type',
                                                        'provider',
                                                        'template'))
    item_name = service_name
    catalog_item = CatalogItem(item_type=item_type,
                               name=item_name,
                               description="my catalog",
                               display_in=True,
                               catalog=catalog,
                               dialog=dialog_name,
                               provider=config_manager_obj,
                               provider_type=provider_type,
                               config_template=template)
    request.addfinalizer(catalog_item.delete)
    return catalog_item


@pytest.mark.tier(2)
@pytest.mark.uncollectif(lambda: version.current_version() < '5.6')
@pytest.mark.ignore_stream("upstream")
@pytest.mark.meta(blockers=['GH#ManageIQ/manageiq-ui-classic:267'])
def test_order_catalog_item(catalog_item, request, logger):
    """Tests order catalog item
    Metadata:
        test_flag: provision
    """
    catalog_item.create()
    service_catalogs = ServiceCatalogs(catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    cells = {'Description': catalog_item.name}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=1400, delay=20)
    assert 'Provisioned Successfully' in row.last_message.text
    DefaultView.set_default_view("Configuration Management Providers", "List View")


@pytest.mark.tier(2)
@pytest.mark.uncollectif(lambda: version.current_version() < '5.6')
@pytest.mark.ignore_stream("upstream")
@pytest.mark.meta(blockers=[BZ(1420179, forced_streams=["5.6", "5.7", "upstream"])])
def test_retire_ansible_service(catalog_item, request, logger):
    """Tests order catalog item
    Metadata:
        test_flag: provision
    """
    catalog_item.create()
    service_catalogs = ServiceCatalogs(catalog_item.name)
    service_catalogs.order()
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    cells = {'Description': catalog_item.name}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=1400, delay=20)
    assert 'Provisioned Successfully' in row.last_message.text
    myservice = MyService(catalog_item.name)
    myservice.retire()
    # this is to assert that service is deleted from VMDB after retirement
    assert(myservice.exists()) is False
