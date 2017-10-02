from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.utils import Parameter, ParametrizedLocator, ParametrizedString
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
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigate_to, navigator, CFMENavigateStep
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for
from . import ServicesCatalogView
from cfme.common import WidgetasticTaggable, TagPageView


class BootstrapSelect(VanillaBootstrapSelect):
    """BootstrapSelect widget for Ansible Playbook Catalog Item form.

    BootstrapSelect widgets don't have `data-id` attribute in this form, so we have to override ROOT
    locator.

    """
    ROOT = ParametrizedLocator('.//select[normalize-space(@name)={@id|quote}]/..')


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
        return list(set(self.all_vars) - set(values))

    def _values_to_add(self, values):
        return list(set(values) - set(self.all_vars))

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
    class provisioning(Tab):  # noqa
        repository = BootstrapSelect("provisioning_repository_id")
        playbook = BootstrapSelect("provisioning_playbook_id")
        machine_credential = BootstrapSelect("provisioning_machine_credential_id")
        cloud_type = BootstrapSelect("provisioning_cloud_type")
        hosts = Input("provisioning_inventory")
        max_ttl = Input("provisioning_execution_ttl")
        escalate_privilege = BootstrapSwitch("provisioning_become_enabled")
        verbosity = BootstrapSelect("provisioning_verbosity")
        use_exisiting = Checkbox(locator=".//label[normalize-space(.)='Use Existing']/input")
        create_new = Checkbox(locator=".//label[normalize-space(.)='Create New']/input")
        provisioning_dialog_id = BootstrapSelect("provisioning_dialog_id")
        provisioning_dialog_name = Input(name="vm.provisioning_dialog_name")
        extra_vars = AnsibleExtraVariables(tab="provisioning")

    @View.nested
    class retirement(Tab):  # noqa
        # TODO Somehow need to handle a modal window
        copy_from_provisioning = Button("Copy from provisioning")
        repository = BootstrapSelect("retirement_repository_id")
        playbook = BootstrapSelect("retirement_playbook_id")
        machine_credential = BootstrapSelect("retirement_machine_credential_id")
        cloud_type = BootstrapSelect("retirement_cloud_type")
        hosts = Input("retirement_inventory")
        max_ttl = Input("retirement_execution_ttl")
        escalate_privilege = BootstrapSwitch("retirement_become_enabled")
        verbosity = BootstrapSelect("retirement_verbosity")
        remove_resources = BootstrapSelect("vm.catalogItemModel.retirement_remove_resources")
        extra_vars = AnsibleExtraVariables(tab="retirement")

    cancel = Button("Cancel")


class SelectCatalogItemTypeView(ServicesCatalogView):
    title = Text(".//span[@id='explorer_title_text']")
    catalog_item_type = BootstrapSelect("st_prov_type", can_hide_on_select=True)
    add = Button("Add")
    cancel = Button("Cancel")

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
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


class DetailsEntitiesAnsibleCatalogItemView(View):
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


class DetailsAnsibleCatalogItemView(ServicesCatalogView):
    """Has to be in view standards, changed for WidgetasticTaggable.get_tags()"""
    entities = View.nested(DetailsEntitiesAnsibleCatalogItemView)

    @property
    def is_displayed(self):
        return (
            self.in_explorer and
            self.entities.title.text == 'Service Catalog Item "{}"'.format(
                self.context["object"].name
            )
        )


class AnsiblePlaybookCatalogItem(Updateable, Navigatable, WidgetasticTaggable):
    """Represents Ansible Playbook catalog item.

    Example:

        .. code-block:: python

            from cfme.services.catalogs.ansible_catalog_item import AnsiblePlaybookCatalogItem
            catalog_item = AnsiblePlaybookCatalogItem(
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
            catalog_item.create()
            catalog_item.delete()

    Args:
        name (str): catalog item name
        description (str): catalog item description
        provisioning (dict): provisioning data
        catalog (py:class:`cfme.services.catalogs.catalog.Catalog`): catalog object
        display_in_catalog (bool): whether this playbook displayed in catalog
        retirement (dict): retirement data
    """

    def __init__(self, name, description, provisioning, display_in_catalog=None, catalog=None,
            retirement=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.description = description
        self.display_in_catalog = display_in_catalog
        self.catalog = catalog
        self.provisioning = provisioning
        self.retirement = retirement

    def create(self):
        view = navigate_to(self, "Add")
        view.fill({
            "name": self.name,
            "description": self.description,
            "display_in_catalog": self.display_in_catalog,
            "catalog": getattr(self.catalog, "name", None),
        })
        view.provisioning.fill({
            "repository": self.provisioning["repository"]
        })
        # After filling "repository" we have to wait for a while until other widgets appeared
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
            "extra_vars": self.provisioning.get("extra_vars"),
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
                "verbosity": self.retirement.get("verbosity"),
                "extra_vars": self.retirement.get("extra_vars")
            })
        view.add.click()
        view = self.create_view(AllCatalogItemView)
        assert view.is_displayed
        view.flash.assert_success_message("Catalog Item {} was added".format(self.name))

    def update(self, updates):
        view = navigate_to(self, "Edit")
        general_changed = view.fill({
            "name": updates.get("name"),
            "description": updates.get("description"),
            "display_in_catalog": updates.get("display_in_catalog"),
            "catalog": getattr(updates.get("catalog"), "name", None),
            "provisioning": updates.get("provisioning")
        })
        retirement_changed = False
        if "retirement" in updates:
            view.retirement.fill({
                "repository": updates["retirement"]["repository"]
            })
            wait_for(lambda: view.retirement.playbook.is_displayed, delay=0.5, num_sec=2)
            view.retirement.fill({
                "playbook": updates["retirement"]["playbook"],
                "machine_credential": updates["retirement"]["machine_credential"],
                "cloud_type": updates["retirement"].get("cloud_type"),
                "hosts": updates["retirement"].get("hosts"),
                "escalate_privilege": updates["retirement"].get("escalate_privilege"),
                "verbosity": updates["retirement"].get("verbosity")
            })
            retirement_changed = True
        if general_changed or retirement_changed:
            view.save.click()
            msg = "Catalog Item {} was saved".format(updates.get("name", self.name))
        else:
            view.cancel.click()
            msg = "Edit of Catalog Item {} was cancelled by the user".format(self.name)
        view = self.create_view(DetailsAnsibleCatalogItemView, override=updates)
        assert view.is_displayed
        view.flash.assert_success_message(msg)

    def delete(self, cancel=False):
        view = navigate_to(self, "Details")
        view.configuration.item_select("Remove Catalog Item", handle_alert=not cancel)
        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
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
    prerequisite = NavigateToAttribute("appliance.server", "ServicesCatalog")

    def step(self):
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


@navigator.register(AnsiblePlaybookCatalogItem, "PickItemType")
class PickItemType(CFMENavigateStep):
    VIEW = SelectCatalogItemTypeView
    prerequisite = NavigateToSibling("All")

    def step(self):
        self.prerequisite_view.configuration.item_select("Add a New Catalog Item")


@navigator.register(AnsiblePlaybookCatalogItem, "Add")
class Add(CFMENavigateStep):
    VIEW = AddAnsibleCatalogItemView
    prerequisite = NavigateToSibling("PickItemType")

    def step(self):
        self.prerequisite_view.catalog_item_type.select_by_visible_text("Ansible Playbook")


@navigator.register(AnsiblePlaybookCatalogItem, "Edit")
class Edit(CFMENavigateStep):
    VIEW = EditAnsibleCatalogItemView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.configuration.item_select("Edit this Item")


@navigator.register(AnsiblePlaybookCatalogItem, 'EditTagsFromDetails')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.policy.item_select('Edit Tags')
