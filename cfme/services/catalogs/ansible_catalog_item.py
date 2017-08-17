from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.utils import ParametrizedLocator
from widgetastic.widget import Checkbox, Table, Text, View
from widgetastic_manageiq import FileInput, SummaryForm, SummaryTable
from widgetastic_patternfly import (
    BootstrapSelect as VanillaBootstrapSelect,
    BootstrapSwitch,
    Button,
    Input,
    Tab
)

from cfme.services.catalogs.catalog_item import AllCatalogItemView
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigate_to, navigator, CFMENavigateStep
from utils.update import Updateable
from utils.wait import wait_for
from . import ServicesCatalogView


class BootstrapSelect(VanillaBootstrapSelect):
    """BootstrapSelect widget for Ansible Playbook Catalog Item form.

    BootstrapSelect widgets don't have `data-id` attribute, so we have to override ROOT locator.

    """
    ROOT = ParametrizedLocator('.//select[normalize-space(@name)={@id|quote}]/..')


class AnsibleCatalogItemForm(ServicesCatalogView):
    title = Text(".//span[@id='explorer_title_text']")
    name = Input("name")
    description = Input("description")
    display_in_catalog = BootstrapSwitch(name="display")
    catalog = BootstrapSelect("catalog_id")

    @View.nested
    class provisioning(Tab):  # noqa
        repository = BootstrapSelect("provisioning_repository_id")
        playbook = BootstrapSelect("provisioning_playbook_id")
        machine_credential = BootstrapSelect("provisioning_machine_credential_id")
        cloud_type = BootstrapSelect("provisioning_cloud_type")
        hosts = Input("provisioning_inventory")
        escalate_privilege = BootstrapSwitch("provisioning_become_enabled")
        verbosity = BootstrapSelect("provisioning_verbosity")
        use_exisiting = Checkbox(locator=".//label[normalize-space(.)='Use Existing']/input")
        create_new = Checkbox(locator=".//label[normalize-space(.)='Create New']/input")
        provisioning_dialog_id = BootstrapSelect("provisioning_dialog_id")
        provisioning_dialog_name = Input(name="vm.provisioning_dialog_name")

    @View.nested
    class retirement(Tab):  # noqa
        # TODO Somehow need to handle a modal window
        copy_from_provisioning = Button("Copy from provisioning")
        repository = BootstrapSelect("retirement_repository_id")
        playbook = BootstrapSelect("provisioning_playbook_id")
        machine_credential = BootstrapSelect("provisioning_machine_credential_id")
        cloud_type = BootstrapSelect("provisioning_cloud_type")
        hosts = Input("retirement_inventory")
        escalate_privilege = BootstrapSwitch(name="provisioning_become_enabled")
        verbosity = BootstrapSelect("retirement_verbosity")
        remove_resources = BootstrapSelect("vm.catalogItemModel.retirement_remove_resources")

    cancel = Button("Cancel")


class SelectCatalogItemTypeView(ServicesCatalogView):
    title = Text(".//span[@id='explorer_title_text']")
    catalog_item_type = BootstrapSelect("st_prov_type", can_hide_on_select=True)
    add = Button("Add")
    cancel = Button("Cancel")

    @property
    def is_displayed(self):
        return (
            self.in_explorer() and
            self.title.text == "Adding a new Service Catalog Item" and
            self.catalog_item_type.is_displayed
        )


class AddAnsibleCatalogItemView(AnsibleCatalogItemForm):
    add = Button("Add")

    @property
    def is_displayed(self):
        return False


class EditAnsibleCatalogItemView(AnsibleCatalogItemForm):
    save = Button("Save")
    reset = Button("Reset")

    @property
    def is_displayed(self):
        return False


class DetailsAnsibleCatalogItemView(ServicesCatalogView):
    title = Text(".//span[@id='explorer_title_text']")
    basic_information = SummaryForm("Basic Information")
    custom_image = FileInput("upload_image")
    upload = Button("Upload")
    smart_management = SummaryTable("Smart Management")

    @View.nested
    class provisioning(Tab):  # noqa
        info = SummaryForm("Provisioning Info")
        variables_and_default_values = Table(".//div[@id='provisioning']//table")

    @View.nested
    class retirement(Tab):  # noqa
        info = SummaryForm("Retirement Info")
        variables_and_default_values = Table(".//div[@id='retirement']//table")

    @property
    def is_displayed(self):
        return (
            self.in_explorer() and
            self.title.text == 'Service Catalog Item "{}"'.format(self.context["object"].name)
        )


class AnsiblePlaybookCatalogItem(Updateable, Navigatable):

    def __init__(self, name, description, display_in_catalog=None, catalog=None, provisioning=None,
            retirement=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.description = description
        self.display_in_catalog = display_in_catalog
        self.catalog = getattr(catalog, "name", None)
        self.provisioning = provisioning
        self.retirement = retirement

    def create(self):
        view = navigate_to(self, "Add")
        view.fill({
            "name": self.name,
            "description": self.description,
            "display_in_catalog": self.display_in_catalog,
            "catalog": self.catalog,
        })
        view.provisioning.fill({
            "repository": self.provisioning["repository"]
        })
        wait_for(lambda: view.provisioning.playbook.is_displayed, delay=0.5, num_sec=2)
        view.provisioning.fill({
            "playbook": self.provisioning["playbook"],
            "machine_credential": self.provisioning["machine_credential"],
            "cloud_type": self.provisioning.get("cloud_type"),
            "hosts": self.provisioning.get("hosts"),
            "escalate_privilege": self.provisioning.get("escalate_privilege"),
            "verbosity": self.provisioning.get("verbosity"),
            "use_exisiting": self.provisioning.get("use_exisiting"),
            "create_new": self.provisioning.get("create_new"),
            "provisioning_dialog_id": self.provisioning.get("provisioning_dialog_id"),
            "provisioning_dialog_name": self.provisioning.get("provisioning_dialog_name")
        })
        if self.retirement is not None:
            view.retirement.fill({
                "repository": self.retirement["repository"]
            })
            wait_for(lambda: view.retirement.playbook.is_displayed, delay=0.5, num_sec=2)
            view.retirement.fill({
                "playbook": self.retirement["playbook"],
                "machine_credential": self.retirement["machine_credential"],
                "cloud_type": self.retirement.get("cloud_type"),
                "hosts": self.retirement.get("hosts"),
                "escalate_privilege": self.retirement.get("escalate_privilege"),
                "verbosity": self.retirement.get("verbosity")
            })
        view.add.click()
        view = self.create_view(AllCatalogItemView)
        assert view.is_displayed
        view.flash.assert_success_message("Catalog Item {} was added".format(self.name))

    def update(self, updates):
        view = navigate_to(self, "Edit")
        changed = view.fill(updates)
        if changed:
            view.save.click()
            msg = "Catalog Item {} was saved".format(updates.get("name") or self.name)
        else:
            view.cancel.click()
            msg = "Edit of Catalog Item {} was cancelled by the user".format(self.name)
        view = self.create_view(DetailsAnsibleCatalogItemView, override=updates)
        assert view.is_displayed
        view.flash.assert_success_message(msg)

    def delete(self):
        view = navigate_to(self, "Details")
        view.configuration.item_select("Remove Catalog Item")
        view = self.create_view(AllCatalogItemView)
        assert view.is_displayed
        view.flash.assert_success_message("The selected Catalog Item was deleted")

    @property
    def exists(self):
        try:
            navigate_to(self, "Details")
        except Exception:
            return False
        else:
            return True


@navigator.register(AnsiblePlaybookCatalogItem, "All")
class All(CFMENavigateStep):
    VIEW = AllCatalogItemView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self):
        self.prerequisite_view.navigation.select("Services", "Catalogs")
        self.view.catalog_items.tree.click_path("All Catalog Items")


@navigator.register(AnsiblePlaybookCatalogItem, "Details")
class Details(CFMENavigateStep):
    VIEW = DetailsAnsibleCatalogItemView
    prerequisite = NavigateToSibling("All")

    def step(self):
        tree = self.prerequisite_view.catalog_items.tree
        tree.click_path(
            "All Catalog Items",
            getattr(self.obj.catalog, "name", "Unassigned"),
            self.obj.name
        )


@navigator.register(AnsiblePlaybookCatalogItem, "Add")
class Add(CFMENavigateStep):
    VIEW = AddAnsibleCatalogItemView
    prerequisite = NavigateToSibling("All")

    def step(self):
        self.prerequisite_view.configuration.item_select("Add a New Catalog Item")
        view = self.prerequisite_view.browser.create_view(SelectCatalogItemTypeView)
        view.catalog_item_type.select_by_visible_text("Ansible Playbook")


@navigator.register(AnsiblePlaybookCatalogItem, "Edit")
class Edit(CFMENavigateStep):
    VIEW = EditAnsibleCatalogItemView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.configuration.item_select("Edit this Item")
