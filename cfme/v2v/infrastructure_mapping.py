import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.utils import ParametrizedLocator
from widgetastic.utils import WaitFillViewStrategy
from widgetastic.widget import ParametrizedView
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import SelectorDropdown
from widgetastic_patternfly import Text
from widgetastic_patternfly import TextInput

from cfme.base.login import BaseLoggedInPage
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker
from widgetastic_manageiq import InfraMappingList
from widgetastic_manageiq import InfraMappingTreeView
from widgetastic_manageiq import MultiSelectList
from widgetastic_manageiq import V2VFlashMessages
from widgetastic_manageiq import V2VPaginatorPane


class InfrastructureMappingView(BaseLoggedInPage):
    title = Text("#explorer_title_text")

    @property
    def in_mapping_explorer(self):
        nav_menu = (
            ["Compute", "Migration", "Infrastructure Mappings"]
            if self.context["object"].appliance.version < "5.11"
            else ["Migration", "Infrastructure Mappings"]
        )
        return self.logged_in_as_current_user and (self.navigation.currently_selected == nav_menu)

    @property
    def is_displayed(self):
        return self.in_mapping_explorer


class InfraMappingCommonButtons(InfrastructureMappingView):
    back_btn = Button("Back")
    next_btn = Button("Next")
    cancel_btn = Button("Cancel")
    save = Button("Save")
    create_btn = Button("Create")
    add_mapping = Button("Add Mapping")
    remove_mapping = Button("Remove Selected")
    remove_all_mappings = Button("Remove All")
    mappings_tree = InfraMappingTreeView(tree_class="treeview")


class ComponentView(View):
    buttons = View.include(InfraMappingCommonButtons, use_parent=True)
    comp_name = None

    @ParametrizedView.nested
    class MappingFillView(ParametrizedView):
        PARAMETERS = ("object_type",)

        source = MultiSelectList(ParametrizedLocator("source_{object_type}"))
        target = MultiSelectList(ParametrizedLocator("target_{object_type}"))
        fill_strategy = WaitFillViewStrategy("15s")

        def after_fill(self, was_change):
            if not self.parent.add_mapping.disabled:
                self.parent.add_mapping.click()

        @property
        def is_displayed(self):
            return (self.source.is_displayed and
                    (len(self.browser.elements(".//div[contains(@class,'spinner')]")) == 0))

    def fill(self, values):
        was_change = True
        for mapping in values:
            self.MappingFillView(self.comp_name).fill(mapping)
        else:
            was_change = False
        self.after_fill(was_change)
        return was_change

    def after_fill(self, was_change):
        self.next_btn.click()


class InfrastructureMappingForm(InfrastructureMappingView):
    """All infrastructure mapping View"""

    title = Text(locator='.//h4[contains(@class,"modal-title")]')

    @property
    def is_displayed(self):
        return self.title.text == self.form_title_text

    @View.nested
    class general(InfraMappingCommonButtons):  # noqa
        name = TextInput(name="name")
        description = TextInput(name="description")
        plan_type = BootstrapSelect("targetProvider")
        name_help_text = Text(locator='.//div[contains(@id,"name")]/span')
        description_help_text = Text(locator='.//div[contains(@id,"description")]/span')
        flash = V2VFlashMessages('.//div[@class="modal-wizard-alert"]')
        fill_strategy = WaitFillViewStrategy()

        def after_fill(self, was_change):
            if was_change:
                self.next_btn.click()

    @View.nested
    class cluster(ComponentView): # noqa
        comp_name = "cluster"

    @View.nested
    class datastore(ComponentView): # noqa
        comp_name = "datastore"

    @View.nested
    class network(ComponentView): # noqa
        comp_name = "network"

        def after_fill(self, was_change):
            if self.create_btn.is_displayed:
                self.create_btn.click()
            elif self.save.is_displayed:
                self.save.click()

    @View.nested
    class result(View):  # noqa
        close_btn = Button("Close")
        continue_to_plan_wizard = Button("Continue to the plan wizard")
        success_icon = Text('.//div[contains(@class,"wizard-pf-success-icon")]')

    def after_fill(self, was_change):
        if was_change:
            self.result.close_btn.click()


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


class EditInfrastructureMappingView(InfrastructureMappingForm):
    form_title_text = "Edit Infrastructure Mapping"
    save = Button("Save")


@attr.s
class InfrastructureMapping(BaseEntity):
    """Class representing v2v infrastructure mappings
    A mapping consists of datastore/network/cluster components
    Each component is a list of source -> target mappings, which are many:many relationships
    """

    @attr.s
    class InfraMappingComponent(object):
        """A datastore/network/cluster mapping component
        Modeling a many:many relationship of a single component mapping
        """

        comp_name = None

        sources = attr.ib(validator=attr.validators.instance_of(list))
        targets = attr.ib(validator=attr.validators.instance_of(list))

        def fill_dict(self):
            return {"source": self.sources, "target": self.targets}

    @attr.s
    class ClusterComponent(InfraMappingComponent):
        comp_name = "cluster"

    @attr.s
    class DatastoreComponent(InfraMappingComponent):
        comp_name = "datastore"

    @attr.s
    class NetworkComponent(InfraMappingComponent):
        comp_name = "network"

    name = attr.ib()
    description = attr.ib()
    plan_type = attr.ib()
    clusters = attr.ib(validator=attr.validators.instance_of(list))
    datastores = attr.ib(validator=attr.validators.instance_of(list))
    networks = attr.ib(validator=attr.validators.instance_of(list))

    def fill_dict(self, target_selection=True):
        """Generate a dictionary for filling the InfraMapping wizard
        This is a dictionary which contains 3 lists, for the 3 components
        Each component list has dictionary elements, that contain source + target mapping lists
        Example:
            {'cluster':
                [
                    {'source_cluster': ['test_source'], 'target_cluster': ['test_target']},
                    {'source_cluster: ['source1', 'source2'], 'target_cluster: ['t1', 't2']
                ]
            }
        Returns: dict, see above
        """
        target_provider = (("Red Hat Virtualization" if self.plan_type == "rhv"
                           else "Red Hat OpenStack Platform") if target_selection else None)
        return {
            "general": {"name": self.name, "description": self.description,
                        "plan_type": target_provider},
            "cluster": [component.fill_dict() for component in self.clusters],
            "datastore": [component.fill_dict() for component in self.datastores],
            "network": [component.fill_dict() for component in self.networks],
        }

    def update(self, updates):
        """
        Args:
            updates: An entity instance, that we can call form_values on
        Returns:
        """
        view = navigate_to(self, "Edit", wait_for_view=20)
        self.name = updates.get('name')
        self.description = updates.get('description')
        self.clusters = updates.get('clusters')
        self.datastores = updates.get('datastores')
        self.networks = updates.get('networks')
        view.fill(self.fill_dict(target_selection=False))


@attr.s
class InfrastructureMappingCollection(BaseCollection):
    """Collection object for Migration mapping object"""

    ENTITY = InfrastructureMapping

    def create(self, name, description, plan_type,
               clusters, datastores, networks,
               *args, **kwargs):
        mapping = self.instantiate(
            name, description, plan_type, clusters, datastores, networks, *args, **kwargs
        )
        view = navigate_to(self, "Add")
        view.fill(mapping.fill_dict())
        return mapping

    def mapping_exists(self, mapping_name):
        view = navigate_to(self, "All")
        if self.appliance.version >= "5.10":
            view.items_on_page.item_select("15")
        print(mapping_name)
        return mapping_name in view.infra_mapping_list.read()

    def delete(self, mapping):
        view = navigate_to(self, "All", wait_for_view=20)
        if self.mapping_exists(mapping.name):
            mapping_list = view.infra_mapping_list
            mapping_list.delete_mapping(mapping.name)


@navigator.register(InfrastructureMappingCollection, "All")
class AllMappings(CFMENavigateStep):
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")
    VIEW = AllInfraMappingView

    def step(self):
        if self.obj.appliance.version < "5.11":
            self.prerequisite_view.navigation.select(
                "Compute", "Migration", "Infrastructure Mappings"
            )
        else:
            self.prerequisite_view.navigation.select("Migration", "Infrastructure Mappings")


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
