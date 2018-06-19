import attr

from navmazing import NavigateToAttribute, NavigateToSibling
from selenium.webdriver.common.keys import Keys
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import View
from widgetastic_patternfly import Text, TextInput, Button, BootstrapSelect, SelectorDropdown
from widgetastic.utils import ParametrizedLocator
from widgetastic_manageiq import (
    InfraMappingTreeView, MultiSelectList, MigrationPlansList, InfraMappingList,
    MigrationPlanRequestDetailsList, Paginator)

from cfme.base.login import BaseLoggedInPage
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


# Widgets

class MigrationPlanRequestDetailsPaginator(Paginator):
    """ Represents Paginator control for V2V."""

    PAGINATOR_CTL = './/div[contains(@class,"form-group")][./ul]'
    './input[contains(@class,"pagination-pf-page")]'
    CUR_PAGE_CTL = './/span[./span[contains(@class,"pagination-pf-items-current")]]'
    PAGE_BUTTON_CTL = './/li/a[contains(@title,{})]'

    def next_page(self):
        self._click_button('Next Page')

    def prev_page(self):
        self._click_button('Previous Page')

    def last_page(self):
        self._click_button('Last Page')

    def first_page(self):
        self._click_button('First Page')

    def page_info(self):
        return self.browser.text(self.browser.element(self.CUR_PAGE_CTL, parent=self._paginator))


class MigrationPlanRequestDetailsPaginationDropup(SelectorDropdown):
    ROOT = ParametrizedLocator(
        './/div[contains(@class, "dropup") and ./button[@{@b_attr}={@b_attr_value|quote}]]')


class MigrationPlanRequestDetailsPaginationPane(View):
    """ Represents Paginator Pane for V2V."""

    ROOT = './/form[contains(@class,"content-view-pf-pagination")]'

    items_on_page = MigrationPlanRequestDetailsPaginationDropup('id', 'pagination-row-dropdown')
    paginator = MigrationPlanRequestDetailsPaginator()


# Views


class InfraMappingFormControlButtons(View):
    # common footer buttons for first 3 pages
    back_btn = Button('Back')
    next_btn = Button('Next')
    cancel_btn = Button('Cancel')


class InfraMappingWizardCommon(View):

    add_mapping = Button('Add Mapping')
    remove_mapping = Button('Remove Selected')
    remove_all_mappings = Button('Remove All')
    mappings_tree = InfraMappingTreeView(tree_class='treeview')


class InfraMappingWizardGeneralView(View):
    name = TextInput(name='name')
    description = TextInput(name='description')
    include_buttons = View.include(InfraMappingFormControlButtons)

    def after_fill(self, was_change):
        if was_change:
            self.next_btn.click()


class InfraMappingWizardClustersView(View):
    include_buttons_set1 = View.include(InfraMappingFormControlButtons)
    include_buttons_set2 = View.include(InfraMappingWizardCommon)
    source_clusters = MultiSelectList('source_clusters')
    target_clusters = MultiSelectList('target_clusters')

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
        source_clusters_filled = []
        target_clusters_filled = []
        for mapping in values['mappings']:
            source_clusters_filled.append(self.source_clusters.fill(mapping['sources']))
            target_clusters_filled.append(self.target_clusters.fill(mapping['target']))
            self.add_mapping.click()
        was_change = any(source_clusters_filled) and any(target_clusters_filled)
        if was_change:
            self.next_btn.click()
        return was_change


class InfraMappingWizardDatastoresView(View):
    include_buttons_set1 = View.include(InfraMappingFormControlButtons)
    include_buttons_set2 = View.include(InfraMappingWizardCommon)
    source_datastores = MultiSelectList('source_datastores')
    target_datastores = MultiSelectList('target_datastores')
    cluster_selector = BootstrapSelect(id='cluster_select')

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
        source_datastores_filled = []
        target_datastores_filled = []
        for cluster in values:
            self.cluster_selector.fill(cluster)
            for mapping in values[cluster]['mappings']:
                source_datastores_filled.append(self.source_datastores.fill(mapping['sources']))
                target_datastores_filled.append(self.target_datastores.fill(mapping['target']))
                self.add_mapping.click()
        was_change = any(source_datastores_filled) and any(target_datastores_filled)
        if was_change:
            self.next_btn.click()
        return was_change


class InfraMappingWizardNetworksView(View):
    include_buttons_set1 = View.include(InfraMappingFormControlButtons)
    include_buttons_set2 = View.include(InfraMappingWizardCommon)
    source_networks = MultiSelectList('source_networks')
    target_networks = MultiSelectList('target_networks')
    next_btn = Button("Create")  # overriding, since 'Next' is called 'Create' in this form
    cluster_selector = BootstrapSelect(id='cluster_select')

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
        source_networks_filled = []
        target_networks_filled = []
        for cluster in values:
            self.cluster_selector.fill(cluster)
            for mapping in values[cluster]['mappings']:
                source_networks_filled.append(self.source_networks.fill(mapping['sources']))
                target_networks_filled.append(self.target_networks.fill(mapping['target']))
                self.add_mapping.click()
        was_change = any(source_networks_filled) and any(target_networks_filled)
        if was_change:
            self.next_btn.click()
        return was_change


class InfraMappingWizardResultsView(View):
    close_btn = Button("Close")
    continue_to_plan_wizard_btn = Button("Continue to the plan wizard")


class InfraMappingWizard(View):
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
            self.result.close_btn.click()


class MigrationDashboardView(BaseLoggedInPage):
    create_infrastructure_mapping = Text(locator='(//a|//button)'
        '[text()="Create Infrastructure Mapping"]')
    create_migration_plan = Text(locator='(//a|//button)[text()="Create Migration Plan"]')
    migration_plans_not_started_list = MigrationPlansList("plans-not-started-list")
    migration_plans_completed_list = MigrationPlansList("plans-complete-list")
    infra_mapping_list = InfraMappingList("infra-mappings-list-view")

    @property
    def is_displayed(self):
        return self.navigation.currently_selected == ['Compute', 'Migration']


class AddInfrastructureMappingView(View):
    form = InfraMappingWizard()

    @property
    def is_displayed(self):
        return self.form.title.text == 'Infrastructure Mapping Wizard'


class AddMigrationPlanView(View):
    title = Text(locator='.//h4[contains(@class,"modal-title")]')
    name = TextInput(name='name')
    description = TextInput(name='description')
    back_btn = Button('Back')
    # Since next is a keyword, suffixing it with btn and other two
    # because want to keep it consistent
    next_btn = Button('Next')
    cancel_btn = Button('Cancel')

    @property
    def is_displayed(self):
        return self.title.text == 'Migration Plan Wizard'


class MigrationPlanRequestDetailsView(View):
    migration_request_details_list = MigrationPlanRequestDetailsList("plan-request-details-list")
    sort_type = SelectorDropdown('id', 'sortTypeMenu')
    paginator_view = View.include(MigrationPlanRequestDetailsPaginationPane, use_parent=True)
    search_box = TextInput(locator=".//div[contains(@class,'input-group')]/input")
    clear_filters = Text(".//a[text()='Clear All Filters']")
    # Used for Ascending/Descending sort
    sort_order = Text(".//button[./span[contains(@class,'sort-direction')]]")
    # Used to select filter_by 'Name' or 'Status'
    filter_by_dropdown = SelectorDropdown('id', 'filterFieldTypeMenu')
    # USed to select specific status from dropdown to filter items by
    filter_by_status_dropdown = SelectorDropdown('id', 'filterCategoryMenu')
    # USed to select sort by options like 'VM Name', 'Started' or 'Status'
    sort_by_dropdown = SelectorDropdown('id', 'sortTypeMenu')

    @property
    def is_displayed(self):
        return self.migration_request_details_list.is_displayed

    def filter_by_vm_name(self, vm_name):
        """Enter VM Name in search box and hit ENTER to filter the list of VMs.

        Args:
            vm_name(str): Takes VM Name as arg.
        """
        try:
            self.filter_by_dropdown.item_select("VM Name")
        except NoSuchElementException:
            self.logger.info("filter_by_dropdown not present, "
                "migration plan may not have started yet.Ignoring.")
        self.search_box.fill(vm_name)
        self.browser.send_keys(Keys.ENTER, self.search_box)

    def get_migration_status_by_vm_name(self, vm_name):
        """Search VM using filter_by_name and return its status.

        Args:
            vm_name(str): Takes VM Name as arg.
        """
        try:
            # Try to clear previously applied filters, if any.
            self.clear_filters.click()
        except NoSuchElementException:
            # Ignore as button won't be visible if there were no filters applied.
            self.logger.info("Clear Filters button not present, ignoring.")
        self.filter_with_vm_name(vm_name)
        status = {"Message": self.migration_request_details_list.get_message_text(vm_name),
        "Description": self.migration_request_details_list.get_progress_description(vm_name),
        "Time Elapsed": self.migration_request_details_list.get_clock(vm_name)}
        return status

    def filter_by_status(self, status):
        """Set filter_by_dropdown to 'Status' and uses status arg by user to set status filter.

        Args:
            status(str): Takes status string as arg. Valid status options are:
            ['Pending', 'Validating', 'Pre-migration', 'Migrating', 'VM Transformations Ccompleted',
             'VM Transformations Failed']
        """
        try:
            self.filter_by_dropdown.item_select("Status")
            self.filter_by_status_dropdown.item_select(status)
        except NoSuchElementException:
            raise ItemNotFound("Migration plan is in Not Started State,"
                " hence filter status dropdown not visible")

    def sort_by(self, option):
        """Sort VM list by using one of the 'Started','VM Name' or 'Status' option.

        Args:
            status(str): Takes status string as arg.
        """
        try:
            self.sort_by_dropdown.item_select(option)
        except NoSuchElementException:
            raise ItemNotFound("Migration plan is in Not Started State,"
                " hence sort_by dropdown not visible")

# Collections Entities


@attr.s
class InfrastructureMapping(BaseEntity):
    """Class representing v2v infrastructure mappings"""
    name = attr.ib()
    description = attr.ib(default=None)
    form_data = attr.ib(default=None)


@attr.s
class InfrastructureMappingCollection(BaseCollection):
    """Collection object for Migration mapping object"""
    ENTITY = InfrastructureMapping

    def create(self, form_data):
        infra_map = self.instantiate(
            name=form_data['general']['name'],
            description=form_data['general'].get('description', ''),
            form_data=form_data
        )
        view = navigate_to(self, 'Add')
        view.form.fill(form_data)
        return infra_map

# TODO: Next Entity and Collection classes are to be filled by Yadnyawalk(ytale),
# which he will submit PR for once my PR merged.


@attr.s
class MigrationPlan(BaseEntity):
    """Class representing v2v Migration Plan"""
    # TODO: Ytale is updating rest of the code in this entity in separate PR.
    category = 'migrationplan'
    string_name = 'Migration Plan'
    name = 'plan1'


@attr.s
class MigrationPlanCollection(BaseCollection):
    """Collection object for Migration Plan object"""
    # TODO: Ytale is updating rest of the code in this collection in separate PR.
    ENTITY = MigrationPlan


# Navigations

@navigator.register(InfrastructureMappingCollection, 'All')
@navigator.register(MigrationPlanCollection, 'All')
class All(CFMENavigateStep):
    VIEW = MigrationDashboardView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Migration')

    def resetter(self):
        """Reset the view"""
        self.view.browser.refresh()


@navigator.register(InfrastructureMappingCollection, 'Add')
class AddInfrastructureMapping(CFMENavigateStep):
    VIEW = AddInfrastructureMappingView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.create_infrastructure_mapping.click()


@navigator.register(MigrationPlanCollection, 'Add')
class AddMigrationPlan(CFMENavigateStep):
    VIEW = AddMigrationPlanView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.create_migration_plan.click()


@navigator.register(MigrationPlanCollection, 'Details')
class MigrationPlanRequestDetails(CFMENavigateStep):
    VIEW = MigrationPlanRequestDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        # TODO: REPLACE self.obj.ENTITY.name by self.obj.name when migration plan
        # entity-collection complete
        self.prerequisite_view.migration_plans_not_started_list.select_plan(self.obj.ENTITY.name)
