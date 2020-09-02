import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.utils import Parameter
from widgetastic.utils import ParametrizedLocator
from widgetastic.utils import ParametrizedString
from widgetastic.widget import Checkbox
from widgetastic.widget import Table
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect as VanillaBootstrapSelect
from widgetastic_patternfly import BootstrapSwitch
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input

from cfme.services.catalogs import ServicesCatalogView
from cfme.services.catalogs.catalog_items import BaseCatalogItem
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import FileInput
from widgetastic_manageiq import SummaryForm
from widgetastic_manageiq import SummaryTable
from widgetastic_manageiq import WaitTab


class BootstrapSelect(VanillaBootstrapSelect):
    """BootstrapSelect widget for Ansible Playbook Catalog Item form.

    BootstrapSelect widgets don't have `data-id` attribute in this form, so we have to override ROOT
    locator.

    """
    ROOT = ParametrizedLocator('.//select[normalize-space(@name)={@id|quote}]/..')

    def fill(self, value):
        # Some BootstrapSelects appears on the page only if another select changed. Therefore we
        # should wait until it appears and only then we can fill it.
        self.wait_displayed()
        return super().fill(value)


class ActionsCell(View):
    edit = Button(
        **{"ng-click": ParametrizedString(
            "vm.editKeyValue('{@tab}', this.key, this.key_value, $index)")}
    )
    delete = Button(
        **{"ng-click": ParametrizedString(
            "vm.removeKeyValue('{@tab}', this.key, this.key_value, $index)")}
    )

    def __init__(self, parent, tab, logger=None):
        View.__init__(self, parent, logger=logger)
        self.tab = parent.parent.parent.parent.tab


class AnsibleExtraVariables(View):
    """Represents extra variables part of ansible service catalog edit form.

    Args:
        tab (str): tab name where this view is located. Can be "provisioning" or "retirement".

    """

    variable = Input(name=ParametrizedString("{@tab}_key"))
    default_value = Input(name=ParametrizedString("{@tab}_value"))
    add = Button(**{"ng-click": ParametrizedString("vm.addKeyValue('{@tab}')")})
    variables_table = Table(
        ".//div[@id='variables_div']//table",
        column_widgets={"Actions": ActionsCell(tab=Parameter("@tab"))}
    )

    def __init__(self, parent, tab, logger=None):
        View.__init__(self, parent, logger=logger)
        self.tab = tab

    def _values_to_remove(self, values):
        return list(map(tuple, set(self.all_vars) - set(values)))

    def _values_to_add(self, values):
        return list(map(tuple, set(values) - set(self.all_vars)))

    def fill(self, values):
        """

        Args:
            values (list): [] to remove all vars or [("var", "value"), ...] to fill the view.

        """
        if set(values) == set(self.all_vars):
            return False
        else:
            for value in self._values_to_remove(values):
                rows = list(self.variables_table)
                for row in rows:
                    if row[0].text == value[0]:
                        row["Actions"].widget.delete.click()
                        break
            for value in self._values_to_add(values):
                self.variable.fill(value[0])
                self.default_value.fill(value[1])
                self.add.click()
            return True

    @property
    def all_vars(self):
        if self.variables_table.is_displayed:
            return [(row["Variable"].text, row["Default value"].text) for
                    row in self.variables_table]
        else:
            return []

    def read(self):
        return self.all_vars


class AnsibleCatalogItemForm(ServicesCatalogView):
    title = Text(".//span[@id='explorer_title_text']")
    name = Input("name")
    description = Input("description")
    display_in_catalog = BootstrapSwitch(name="display")
    catalog = BootstrapSelect("catalog_id")

    @View.nested
    class provisioning(WaitTab):  # noqa
        repository = BootstrapSelect("provisioning_repository_id")
        playbook = BootstrapSelect("provisioning_playbook_id")
        machine_credential = BootstrapSelect("provisioning_machine_credential_id")
        vault_credential = BootstrapSelect("provisioning_vault_credential_id")
        cloud_type = BootstrapSelect("provisioning_cloud_type")
        cloud_credential = BootstrapSelect("provisioning_cloud_credential_id")
        localhost = Input(id="provisioning_inventory_localhost")
        specify_host_values = Input(id="provisioning_inventory_specify")
        hosts = Input("provisioning_inventory")
        logging_output = BootstrapSelect("provisioning_log_output")
        max_ttl = Input("provisioning_execution_ttl")
        escalate_privilege = BootstrapSwitch(name="provisioning_become_enabled")
        verbosity = BootstrapSelect("provisioning_verbosity")
        use_exisiting = Checkbox(locator=".//label[normalize-space(.)='Use Existing']/input")
        create_new = Checkbox(locator=".//label[normalize-space(.)='Create New']/input")
        provisioning_dialog_id = BootstrapSelect("provisioning_dialog_id")
        provisioning_dialog_name = Input(name="vm.provisioning_dialog_name")
        extra_vars = AnsibleExtraVariables(tab="provisioning")

    @View.nested
    class retirement(WaitTab):  # noqa
        # TODO Somehow need to handle a modal window
        copy_from_provisioning = Button("Copy from provisioning")
        repository = BootstrapSelect("retirement_repository_id")
        playbook = BootstrapSelect("retirement_playbook_id")
        machine_credential = BootstrapSelect("retirement_machine_credential_id")
        vault_credential = BootstrapSelect("provisioning_vault_credential_id")
        cloud_type = BootstrapSelect("retirement_cloud_type")
        cloud_credential = BootstrapSelect("retirement_cloud_credential_id")
        localhost = Input(id="retirement_inventory_localhost")
        specify_host_values = Input(id="retirement_inventory_specify")
        hosts = Input("retirement_inventory")
        logging_output = BootstrapSelect("retirement_log_output")
        max_ttl = Input("retirement_execution_ttl")
        escalate_privilege = BootstrapSwitch("retirement_become_enabled")
        verbosity = BootstrapSelect("retirement_verbosity")
        remove_resources = BootstrapSelect("retirement_remove_resources")
        extra_vars = AnsibleExtraVariables(tab="retirement")

    cancel = Button("Cancel")


class AddAnsibleCatalogItemView(AnsibleCatalogItemForm):
    add = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Adding a new Service Catalog Item' and
            self.provisioning.repository.is_displayed  # this field should be visible
        )


class EditAnsibleCatalogItemView(AnsibleCatalogItemForm):
    save = Button("Save")
    reset = Button("Reset")

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.title.text == 'Editing Service Catalog Item "{}"'.format(
                self.context["object"].name) and self.provisioning.repository.is_displayed
        )


class DetailsEntitiesAnsibleCatalogItemView(View):
    title = Text(".//span[@id='explorer_title_text']")
    basic_information = SummaryForm("Basic Information")
    custom_image = FileInput("upload_image")
    upload = Button("Upload")
    smart_management = SummaryTable("Smart Management")

    @View.nested
    class provisioning(WaitTab):  # noqa
        info = SummaryForm("Provisioning Info")
        variables_and_default_values = Table(".//div[@id='provisioning']//table")

    @View.nested
    class retirement(WaitTab):  # noqa
        info = SummaryForm("Retirement Info")
        variables_and_default_values = Table(".//div[@id='retirement']//table")


class DetailsAnsibleCatalogItemView(ServicesCatalogView):
    """Has to be in view standards, changed for Taggable.get_tags()"""
    entities = View.nested(DetailsEntitiesAnsibleCatalogItemView)

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.entities.title.text == 'Service Catalog Item "{}"'.format(
                self.context["object"].name
            )
        )


@attr.s
class AnsiblePlaybookCatalogItem(BaseCatalogItem):
    """Represents Ansible Playbook catalog item.

    Example:

        .. code-block:: python

            collection = appliance.collections.catalog_items
            catalog_item = collection.create(
                collection.ANSIBLE_PLAYBOOK
                "some_catalog_name",
                "some_description",
                provisioning={
                    "repository": "Some repository",
                    "playbook": "some_playbook.yml",
                    "machine_credential": "CFME Default Credential",
                    "create_new": True,
                    "provisioning_dialog_name": "some_dialog",
                    "extra_vars": [("some_var", "some_value")]
                }
            )
            catalog_item.delete()

    Args:
        name (str): catalog item name
        description (str): catalog item description
        provisioning (dict): provisioning data
        catalog (py:class:`cfme.services.catalogs.catalog.Catalog`): catalog object
        display_in_catalog (bool): whether this playbook displayed in catalog
        retirement (dict): retirement data
    """
    name = attr.ib()
    description = attr.ib()
    provisioning = attr.ib()
    catalog = attr.ib(default=None)
    display_in_catalog = attr.ib(default=None)
    retirement = attr.ib(default=None)
    item_type = "Ansible Playbook"

    @property
    def fill_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "display_in_catalog": self.display_in_catalog,
            "catalog": self.catalog_name if self.catalog else "<Unassigned>",
            "provisioning": self.provisioning,
            "retirement": self.retirement
        }


@navigator.register(AnsiblePlaybookCatalogItem, "Add")
class Add(CFMENavigateStep):
    VIEW = AddAnsibleCatalogItemView
    prerequisite = NavigateToAttribute("parent", "Choose Type")

    def step(self, *args, **kwargs):
        self.prerequisite_view.select_item_type.select_by_visible_text(self.obj.item_type)


@navigator.register(AnsiblePlaybookCatalogItem, "Edit")
class Edit(CFMENavigateStep):
    VIEW = EditAnsibleCatalogItemView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.configuration.item_select("Edit this Item")


@navigator.register(AnsiblePlaybookCatalogItem, "Details")
class Details(CFMENavigateStep):
    VIEW = DetailsAnsibleCatalogItemView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        tree = self.prerequisite_view.catalog_items.tree
        tree.click_path(
            "All Catalog Items",
            getattr(self.obj.catalog, "name", "Unassigned"),
            self.obj.name
        )
