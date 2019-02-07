import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import View
from widgetastic_manageiq import (
    InfraMappingList,
    InfraMappingTreeView,
    MultiSelectList,
    V2VPaginatorPane,
)
from widgetastic_patternfly import Button, SelectorDropdown, Text, TextInput
from widgetastic.utils import WaitFillViewStrategy

from cfme.base.login import BaseLoggedInPage
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.update import Updateable
from cfme.utils.version import Version, VersionPicker

# from cfme.v2v.migration_plans import MigrationPlanView


class InfrastructureMappingView(BaseLoggedInPage):
    title = Text("#explorer_title_text")

    @property
    def in_explorer(self):
        return self.logged_in_as_current_user and (
            self.navigation.currently_selected
            == ["Compute", "Migration", "Infrastructure Mappings"]
        )

    @property
    def is_displayed(self):
        return self.in_explorer


class InfraMappingCommonButtons(InfrastructureMappingView):
    back_btn = Button("Back")
    next_btn = Button("Next")
    cancel_btn = Button("Cancel")
    save = Button("Save")
    create = Button("Create")
    add_mapping = Button("Add Mapping")
    remove_mapping = Button("Remove Selected")
    remove_all_mappings = Button("Remove All")
    mappings_tree = InfraMappingTreeView(tree_class="treeview")


class InfrastructureMappingForm(InfrastructureMappingView):
    """All infrastructure mapping View"""

    title = Text(locator='.//h4[contains(@class,"modal-title")]')

    @View.nested
    class general(InfraMappingCommonButtons):  # noqa
        name = TextInput(name="name")
        description = TextInput(name="description")
        name_help_text = Text(locator='.//div[contains(@id,"name")]/span')
        description_help_text = Text(locator='.//div[contains(@id,"description")]/span')
        fill_strategy = WaitFillViewStrategy()

        def after_fill(self, was_change):
            if was_change:
                self.next_btn.click()

    @View.nested
    class cluster(InfraMappingCommonButtons):  # noqa
        @View.nested
        class cluster_mapping(InfraMappingCommonButtons):  # noqa
            source_cluster = MultiSelectList("source_clusters")
            target_cluster = MultiSelectList("target_clusters")
            fill_strategy = WaitFillViewStrategy()

            def after_fill(self, was_change):
                if not self.add_mapping.disabled:
                    self.add_mapping.click()

        def fill(self, values):
            was_change = True
            for mapping in values.get("mappings", []) if isinstance(values, dict) else []:
                self.cluster_mapping.fill(mapping)
            else:
                was_change = False
            self.after_fill(was_change)
            return was_change

        def after_fill(self, was_change):
            self.next_btn.click()

    @View.nested
    class datastore(InfraMappingCommonButtons):  # noqa
        @View.nested
        class datastore_mapping(InfraMappingCommonButtons):  # noqa
            source_datastore = MultiSelectList("source_datastores")
            target_datastore = MultiSelectList("target_datastores")
            fill_strategy = WaitFillViewStrategy(wait_widget="15s")

            def after_fill(self, was_change):
                if not self.add_mapping.disabled:
                    self.add_mapping.click()

        def fill(self, values):
            was_change = True
            for mapping in values.get("mappings", []) if isinstance(values, dict) else []:
                self.datastore_mapping.fill(mapping)
            else:
                was_change = False
            self.after_fill(was_change)
            return was_change

        def after_fill(self, was_change):
            self.next_btn.click()

    @View.nested
    class network(InfraMappingCommonButtons):  # noqa
        @View.nested
        class network_mapping(InfraMappingCommonButtons):  # noqa
            source_network = MultiSelectList("source_networks")
            target_network = MultiSelectList("target_networks")
            fill_strategy = WaitFillViewStrategy()

            def after_fill(self, was_change):
                if not self.add_mapping.disabled:
                    self.add_mapping.click()

        def fill(self, values):
            was_change = True
            for mapping in values.get("mappings", []) if isinstance(values, dict) else []:
                self.network_mapping.fill(mapping)
            else:
                was_change = False
            self.after_fill(was_change)
            return was_change

        def after_fill(self, was_change):
            if self.create.is_displayed:
                self.create.click()
            elif self.save.is_displayed:
                self.save.click()

    @View.nested
    class result(View):  # noqa
        close = Button("Close")
        continue_to_plan_wizard = Button("Continue to the plan wizard")
        success_icon = Text('.//div[contains(@class,"wizard-pf-success-icon")]')

    def after_fill(self, was_change):
        if was_change:
            self.result.close.click()


class AllInfraMappingView(InfrastructureMappingView):
    """All infrastructure mapping View"""

    infra_mapping_list = InfraMappingList("infra-mappings-list-view")
    create_infra_mapping = Text(locator='(//a|//button)[text()="Create Infrastructure Mapping"]')
    configure_providers = Text(locator='//a[text()="Configure Providers"]')
    paginator_view = View.include(V2VPaginatorPane, use_parent=True)
    search_box = TextInput(locator=".//div[contains(@class,'input-group')]/input")
    clear_filters = Text(".//a[text()='Clear All Filters']")
    sort_order = Text(".//button[./span[contains(@class,'sort-direction')]]")
    filter_by_dropdown = SelectorDropdown("id", "filterFieldTypeMenu")
    sort_by_dropdown = SelectorDropdown("id", "sortTypeMenu")

    @property
    def is_displayed(self):

        return len(self.browser.elements(".//div[contains(@class,'spinner')]")) == 0 and (
            self.create_infra_mapping.is_displayed
            or self.infra_mapping_list.is_displayed
            or self.configure_providers.is_displayed
        )


class AddInfrastructureMappingView(InfrastructureMappingForm):
    form_title_text = VersionPicker(
        {
            Version.lowest(): "Infrastructure Mapping Wizard",
            "5.10": "Create Infrastructure Mapping",
        }
    )

    @property
    def is_displayed(self):
        return self.title.text == self.form_title_text


class EditInfrastructureMappingView(InfrastructureMappingForm):
    form_title_text = "Edit Infrastructure Mapping"
    save = Button("Save")

    @property
    def is_displayed(self):
        return self.title.text == self.form_title_text


@attr.s
class InfrastructureMapping(BaseEntity, Updateable):
    """Class representing v2v infrastructure mappings"""

    name = attr.ib()
    description = attr.ib(default=None)
    form_data = attr.ib(default=None)

    def update(self, updates):
        view = navigate_to(self, "Edit", wait_for_view=20)
        view.fill(updates)


@attr.s
class InfrastructureMappingCollection(BaseCollection):
    """Collection object for Migration mapping object"""

    ENTITY = InfrastructureMapping

    def create(self, form_data):
        view = navigate_to(self, "Add")
        view.fill(form_data)
        return self.instantiate(
            name=form_data["general"]["name"],
            description=form_data["general"].get("description", ""),
            form_data=form_data,
        )

    def find_mapping(self, mapping):
        view = navigate_to(self, "All")
        if self.appliance.version >= "5.10":
            view.items_on_page.item_select("15")
        return mapping.name in view.infra_mapping_list.read()

    def delete(self, mapping):
        view = navigate_to(self, "All", wait_for_view=20)
        if self.find_mapping(mapping):
            mapping_list = view.infra_mapping_list
            mapping_list.delete_mapping(mapping.name)


@navigator.register(InfrastructureMappingCollection, "All")
class AllMappings(CFMENavigateStep):
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")
    # Uncomment when all files are merged
    # VIEW = VersionPicker({Version.lowest(): MigrationPlanView, "5.10": AllInfraMappingView})
    VIEW = AllInfraMappingView

    def step(self):
        if self.obj.appliance.version < "5.10":
            self.prerequisite_view.navigation.select("Compute", "Migration")
        else:
            self.prerequisite_view.navigation.select(
                "Compute", "Migration", "Infrastructure Mappings"
            )


@navigator.register(InfrastructureMappingCollection, "Add")
class AddInfrastructureMapping(CFMENavigateStep):
    VIEW = AddInfrastructureMappingView
    prerequisite = NavigateToSibling("All")

    def step(self):
        self.prerequisite_view.create_infra_mapping.click()


@navigator.register(InfrastructureMapping, "Edit")
class EditInfrastructureMapping(CFMENavigateStep):
    VIEW = EditInfrastructureMappingView

    prerequisite = NavigateToAttribute("parent", "All")

    def step(self):
        if not self.prerequisite_view.infra_mapping_list.edit_mapping(self.obj.name):
            raise ItemNotFound("Mapping {} not found".format(self.obj.name))
