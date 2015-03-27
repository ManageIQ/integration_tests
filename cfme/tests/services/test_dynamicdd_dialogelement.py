import pytest

from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.automate.service_dialogs import ServiceDialog
from cfme.services.catalogs.catalog import Catalog
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.automate.explorer import Domain, Namespace, Class, Method, Instance
from cfme.web_ui import flash
from utils.randomness import generate_random_string
import utils.randomness as rand

pytestmark = [
    pytest.mark.usefixtures("logged_in"),
    pytest.mark.long_running,
    pytest.mark.ignore_stream("5.2"),
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.meta(server_roles="+automate")
]

item_name = generate_random_string()

METHOD_TORSO = """
# Method for logging
def log(level, message)
  @method = 'Service Dialog Provider Select'
  $evm.log(level, "#{@method} - #{message}")
end

# Start Here
log(:info, " - Listing Root Object Attributes:") if @debug
$evm.root.attributes.sort.each { |k, v| $evm.log('info', "#{@method} - \t#{k}: #{v}") if @debug }
log(:info, "===========================================") if @debug

        dialog_field = $evm.object
        dialog_field['data_type'] = 'string'
        dialog_field['required']  = 'true'
        dialog_field['sort_by']   = 'value'
        list = []
        list << ['item_value', 'item_description']
        dialog_field['values'] = list
"""


@pytest.yield_fixture(scope="function")
def dialog(copy_instance, create_method):
    dialog = "dialog_" + generate_random_string()
    element_data = dict(
        ele_label="ele_" + rand.generate_random_string(),
        ele_name=rand.generate_random_string(),
        ele_desc="my ele desc",
        choose_type="Drop Down Dynamic List",
        field_entry_point="InspectMe",
        field_show_refresh_button=True
    )
    service_dialog = ServiceDialog(label=dialog, description="my dialog",
                     submit=True, cancel=True,
                     tab_label="tab_" + rand.generate_random_string(), tab_desc="my tab desc",
                     box_label="box_" + rand.generate_random_string(), box_desc="my box desc")
    service_dialog.create(element_data)
    flash.assert_success_message('Dialog "%s" was added' % dialog)
    yield dialog


@pytest.yield_fixture(scope="function")
def catalog():
    cat_name = "cat_" + generate_random_string()
    catalog = Catalog(name=cat_name,
                  description="my catalog")
    catalog.create()
    yield catalog


@pytest.fixture(scope="function")
def copy_domain(request):
    domain = Domain(name="new_domain", enabled=True)
    domain.create()
    request.addfinalizer(lambda: domain.delete() if domain.exists() else None)
    return domain


@pytest.fixture(scope="function")
def create_method(request, copy_domain):
    method = Method(
        name="InspectMe",
        data=METHOD_TORSO,
        cls=Class(
            name="Request",
            namespace=Namespace(
                name="System",
                parent=copy_domain
            )
        )
    )
    method.create()
    return method


@pytest.fixture(scope="function")
def copy_instance(request, copy_domain):
    miq_domain = Domain(name="ManageIQ (Locked)", enabled=True)
    instance = Instance(
        name="InspectMe",
        cls=Class(
            name="Request",
            namespace=Namespace(
                name="System",
                parent=miq_domain
            )
        )
    )
    instance.copy_to(copy_domain)


def test_dynamicdropdown_dialog(dialog, catalog):
    item_name = generate_random_string()
    catalog_item = CatalogItem(item_type="Generic", name=item_name,
                  description="my catalog", display_in=True, catalog=catalog.name,
                  dialog=dialog)
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_item)
