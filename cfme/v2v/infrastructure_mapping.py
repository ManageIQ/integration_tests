import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import View
from widgetastic_manageiq import (
    InfraMappingList,
    InfraMappingTreeView,
    MultiSelectList,
    V2vPaginatorPane,
)
from widgetastic_patternfly import BootstrapSelect, Button, SelectorDropdown, Text, TextInput

from cfme.base.login import BaseLoggedInPage
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.update import Updateable
from cfme.utils.version import Version, VersionPicker
from cfme.v2v.migration_plans import MigrationPlanView


class InfraMappingWizardCommon(View):
    """Infrastructure Mapping common View"""

    add_mapping = Button("Add Mapping")
    remove_mapping = Button("Remove Selected")
    remove_all_mappings = Button("Remove All")
    mappings_tree = InfraMappingTreeView(tree_class="treeview")


class InfrastructureMappingView(BaseLoggedInPage):
    """All infrastructure mapping View"""

    infra_mapping_list = InfraMappingList("infra-mappings-list-view")
    create_infra_mapping = Text(locator='(//a|//button)[text()="Create Infrastructure Mapping"]')
    configure_providers = Text(locator='//a[text()="Configure Providers"]')
    paginator_view = View.include(V2vPaginatorPane, use_parent=True)
    search_box = TextInput(locator=".//div[contains(@class,'input-group')]/input")
    clear_filters = Text(".//a[text()='Clear All Filters']")
    sort_order = Text(".//button[./span[contains(@class,'sort-direction')]]")
    filter_by_dropdown = SelectorDropdown("id", "filterFieldTypeMenu")
    sort_by_dropdown = SelectorDropdown("id", "sortTypeMenu")

    @property
    def is_displayed(self):
        return (
            (
                self.navigation.currently_selected
                == ["Compute", "Migration", "Infrastructure Mappings"]
            )
            and len(self.browser.elements(".//div[contains(@class,'spinner')]")) == 0
            and (
                self.create_infra_mapping.is_displayed
                or self.infra_mapping_list.is_displayed
                or self.configure_providers.is_displayed
            )
        )


class InfraMappingForm(View):
    # common footer buttons for first 3 pages
    back_btn = Button("Back")
    next_btn = Button("Next")
    cancel_btn = Button("Cancel")

    def after_fill(self, was_change):
        # Cancel button is the common button on all pages so
        # waiting for footer buttons to display
        self.cancel_btn.wait_displayed()
        if self.next_btn.is_displayed:
            self.next_btn.click()
        elif self.save.is_displayed:
            self.save.click()


class InfraMappingWizardGeneralView(InfraMappingForm):
    name = TextInput(name="name")
    description = TextInput(name="description")
    name_help_text = Text(locator='.//div[contains(@id,"name")]/span')
    description_help_text = Text(locator='.//div[contains(@id,"description")]/span')

    def after_fill(self, was_change):
        if was_change:
            self.next_btn.click()

    @property
    def is_displayed(self):
        return self.name.is_displayed and self.description.is_displayed


class InfraMappingWizardClustersView(InfraMappingForm):
    include_buttons_set2 = View.include(InfraMappingWizardCommon)
    source_clusters = MultiSelectList("source_clusters")
    target_clusters = MultiSelectList("target_clusters")

    @property
    def is_displayed(self):
        return (
            self.source_clusters.is_displayed
            and self.target_clusters.is_displayed
            and (len(self.browser.elements(".//div[contains(@class,'spinner')]")) == 0)
        )

    def fill(self, values):
        """Use to add all mappings specified in values.
        Args:
            values:
                format as following:
                    {
                       'mappings': [
                            {
                                'sources':['item1', 'item2'],
                                'target':['item_target']
                            }
                       ]
                       ...
                    }
        """
        for mapping in values.get("mappings", []) if isinstance(values, dict) else []:
            self.source_clusters.fill(mapping["sources"])
            self.target_clusters.fill(mapping["target"])
            self.add_mapping.click()
        was_change = not self.mappings_tree.is_empty
        self.after_fill(was_change)
        return was_change


class InfraMappingWizardDatastoresView(InfraMappingForm):
    include_buttons_set2 = View.include(InfraMappingWizardCommon)
    source_datastores = MultiSelectList("source_datastores")
    target_datastores = MultiSelectList("target_datastores")
    cluster_selector = BootstrapSelect(id="cluster_select")

    @property
    def is_displayed(self):
        return (
            self.source_datastores.is_displayed
            and self.target_datastores.is_displayed
            and (len(self.browser.elements(".//div[contains(@class,'spinner')]")) == 0)
        )

    def fill(self, values):
        """Use to add all mappings specified in values.
        Args:
            values:
                format as following:
                    {
                        'cluster_name': {
                            'mappings': [
                                {
                                    'sources':['item1','item2'],
                                    'target':['item_target']
                                },
                                ...
                            ]
                        },
                        ...
                    }
        """
        for cluster in values if isinstance(values, dict) else []:
            if self.cluster_selector.is_displayed:
                self.cluster_selector.fill(cluster)
            for mapping in values[cluster]["mappings"]:
                self.source_datastores.fill(mapping["sources"])
                self.target_datastores.fill(mapping["target"])
                self.add_mapping.click()
        was_change = not self.mappings_tree.is_empty
        self.after_fill(was_change)
        return was_change


class InfraMappingWizardNetworksView(InfraMappingForm):
    include_buttons_set2 = View.include(InfraMappingWizardCommon)
    source_networks = MultiSelectList("source_networks")
    target_networks = MultiSelectList("target_networks")
    next_btn = Button("Create")  # overriding, since 'Next' is called 'Create' in this form
    cluster_selector = BootstrapSelect(id="cluster_select")

    @property
    def is_displayed(self):
        return (
            self.source_networks.is_displayed
            and self.target_networks.is_displayed
            and (len(self.browser.elements(".//div[contains(@class,'spinner')]")) == 0)
        )

    def fill(self, values):
        """Use to add all mappings specified in values.
        Args:
            values:
                format as following:
                    {
                        'cluster_name': {
                            'mappings': [
                                {
                                    'sources':['item1','item2'],
                                    'target':['item_target']
                                },
                                ...
                            ]
                        },
                        ...
                    }
        """
        for cluster in values if isinstance(values, dict) else []:
            if self.cluster_selector.is_displayed:
                self.cluster_selector.fill(cluster)
            for mapping in values[cluster]["mappings"]:
                self.source_networks.fill(mapping["sources"])
                self.target_networks.fill(mapping["target"])
                self.add_mapping.click()
        was_change = not self.mappings_tree.is_empty
        self.after_fill(was_change)
        return was_change


class InfraMappingWizardResultsView(View):
    close = Button("Close")
    continue_to_plan_wizard = Button("Continue to the plan wizard")

    @property
    def is_displayed(self):
        return self.continue_to_plan_wizard.is_displayed


class InfraMappingWizardView(View):
    """Infrastructure Mapping Wizard Modal Widget.
    Usage:
        fill: takes values of following format:
            {
                'general':
                    {
                        'name':'infra_map_{}'.format(fauxfactory.gen_alphanumeric()),
                        'description':fauxfactory.gen_string("alphanumeric",length=50)
                    },
                'cluster':
                    {
                        'mappings': [
                            {
                                'sources':['Datacenter \ Cluster'],
                                'target':['Default \ Default']
                            }
                        ]
                    },
                'datastore':{
                    'Cluster (Default)': {
                       'mappings':[
                            {
                                'sources':['NFS_Datastore_1','iSCSI_Datastore_1'],
                                'target':['hosted_storage']
                            },
                            {
                                'sources':['h02-Local_Datastore-8GB', 'h01-Local_Datastore-8GB'],
                                'target':['env-rhv41-01-nfs-iso']
                            }
                        ]
                   }
                },
                'network':{
                    'Cluster (Default)': {
                        'mappings': [
                            {
                                'sources':['VM Network','VMkernel'],
                                'target':['ovirtmgmt']
                            },
                            {
                                'sources':['DPortGroup'],
                                'target':['Storage VLAN 33']
                            }
                        ]
                    }
                }
            }
    """

    title = Text(locator='.//h4[contains(@class,"modal-title")]')
    general = View.nested(InfraMappingWizardGeneralView)
    cluster = View.nested(InfraMappingWizardClustersView)
    datastore = View.nested(InfraMappingWizardDatastoresView)
    network = View.nested(InfraMappingWizardNetworksView)
    result = View.nested(InfraMappingWizardResultsView)

    def after_fill(self, was_change):
        if was_change:
            self.result.close.click()


class AddInfrastructureMappingView(InfraMappingForm):
    form = InfraMappingWizardView()
    form_title_text = VersionPicker(
        {
            Version.lowest(): "Infrastructure Mapping Wizard",
            "5.10": "Create Infrastructure Mapping",
        }
    )

    @property
    def is_displayed(self):
        return self.form.title.text == self.form_title_text


class EditInfrastructureMappingView(InfraMappingForm):
    form = InfraMappingWizardView()
    form_title_text = "Edit Infrastructure Mapping"
    save = Button("Save")

    @property
    def is_displayed(self):
        return self.form.title.text == self.form_title_text


@attr.s
class InfrastructureMapping(BaseEntity, Updateable):
    """Class representing v2v infrastructure mappings"""

    name = attr.ib()
    description = attr.ib(default=None)
    form_data = attr.ib(default=None)

    def update(self, updates):
        view = navigate_to(self, "Edit", wait_for_view=20)
        view.form.fill(updates)


@attr.s
class InfrastructureMappingCollection(BaseCollection):
    """Collection object for Migration mapping object"""

    ENTITY = InfrastructureMapping

    def create(self, form_data):
        view = navigate_to(self, "Add")
        view.form.fill(form_data)
        return self.instantiate(
            name=form_data["general"]["name"],
            description=form_data["general"].get("description", ""),
            form_data=form_data,
        )

    def find_mapping(self, mapping):
        view = navigate_to(self, "All")
        if self.appliance.version >= "5.10":  # means 5.10+ or upstream
            view.items_on_page.item_select("15")
            if mapping.name in view.infra_mapping_list.read():
                return True
            # TODO: Remove While loop. It is a DIRTY HACK for now, to be addressed in PR 8075
            # =========================================================
            # while not view.clear_filters.is_displayed:
            #    view.search_box.fill("{}\n\n".format(mapping.name))
            # =========================================================
        return mapping.name in view.infra_mapping_list.read()

    def delete(self, mapping):
        view = navigate_to(self, "All", wait_for_view=20)
        if self.find_mapping(mapping):
            mapping_list = view.infra_mapping_list
            mapping_list.delete_mapping(mapping.name)


@navigator.register(InfrastructureMappingCollection, "All")
class AllMappings(CFMENavigateStep):
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")
    VIEW = VersionPicker({Version.lowest(): MigrationPlanView, "5.10": InfrastructureMappingView})

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
        self.prerequisite_view.wait_displayed()
        self.prerequisite_view.create_infra_mapping.click()


@navigator.register(InfrastructureMapping, "Edit")
class EditInfrastructureMapping(CFMENavigateStep):
    VIEW = EditInfrastructureMappingView

    prerequisite = NavigateToAttribute("parent", "All")

    def step(self):
        if not self.prerequisite_view.infra_mapping_list.edit_mapping(self.obj.name):
            raise ItemNotFound("Mapping {} not found".format(self.obj.name))
