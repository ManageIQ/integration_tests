import fauxfactory
import pytest
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.configure.settings import set_default_view
from utils import testgen, version
from utils.log import logger
from utils.wait import wait_for
from cfme.services import requests
from cfme import test_requirements

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
    set_default_view("Configuration Management Providers", "Grid View")
    if config_manager_obj.type == "ansible":
        config_manager_obj.create(validate=True)
    else:
        config_manager_obj.create()
    yield config_manager_obj
    config_manager_obj.delete()


@pytest.fixture(scope="function")
def dialog():
    dialog = "dialog_" + fauxfactory.gen_alphanumeric()
    element_data = dict(
        ele_label="ele_" + fauxfactory.gen_alphanumeric(),
        ele_name=fauxfactory.gen_alphanumeric(),
        ele_desc="my ele desc",
        choose_type="Text Box",
        default_text_box="default value"
    )
    service_dialog = ServiceDialog(label=dialog, description="my dialog",
                     submit=True, cancel=True,
                     tab_label="tab_" + fauxfactory.gen_alphanumeric(), tab_desc="my tab desc",
                     box_label="box_" + fauxfactory.gen_alphanumeric(), box_desc="my box desc")
    service_dialog.create(element_data)
    return dialog


@pytest.yield_fixture(scope="function")
def catalog():
    catalog = "cat_" + fauxfactory.gen_alphanumeric()
    cat = Catalog(name=catalog,
                  description="my catalog")
    cat.create()
    yield catalog


@pytest.fixture(scope="function")
def catalog_item(config_manager, dialog, catalog):
    config_manager_obj = config_manager
    provisionig_data = config_manager_obj.yaml_data['provisioning_data']
    item_type, provider, template = map(provisionig_data.get,
        ('item_type', 'provider', 'template'))
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type=item_type, name=item_name,
                  description="my catalog", display_in=True, catalog=catalog,
                  dialog=dialog, provider_type=provider, config_template=template)
    return catalog_item


@pytest.mark.tier(2)
@pytest.mark.uncollectif(lambda: version.current_version() < '5.6')
def test_order_catalog_item(catalog_item, request):
    """Tests order catalog item
    Metadata:
        test_flag: provision
    """
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_item)
    logger.info('Waiting for cfme provision request for service {}'.format(catalog_item.name))
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=1400, delay=20)
    assert row.last_message.text == '[EVM] Service [{}] Provisioned Successfully'.\
        format(catalog_item.name)
    set_default_view("Configuration Management Providers", "List View")
