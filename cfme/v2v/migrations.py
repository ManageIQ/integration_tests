import attr
import csv
import tempfile
import time

from navmazing import NavigateToAttribute, NavigateToSibling
from selenium.webdriver.common.keys import Keys
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import Checkbox, View
from widgetastic.utils import ParametrizedLocator
from widgetastic_manageiq import (
    InfraMappingTreeView, MultiSelectList, MigrationPlansList, InfraMappingList, Paginator,
    Table, MigrationPlanRequestDetailsList, RadioGroup, HiddenFileInput, MigrationProgressBar,
    MigrationDashboardStatusCard, Stepper
)
from widgetastic_patternfly import (Text, TextInput, Button, BootstrapSelect, SelectorDropdown,
                                    Dropdown, BreadCrumb)

from cfme.base.login import BaseLoggedInPage
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.update import Updateable
from cfme.utils.version import Version, VersionPicker
from cfme.utils.wait import wait_for

from selenium.common.exceptions import StaleElementReferenceException


# Widgets

class v2vPaginator(Paginator):
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


class v2vPaginationDropup(SelectorDropdown):
    ROOT = ParametrizedLocator(
        './/div[contains(@class, "dropup") and ./button[@{@b_attr}={@b_attr_value|quote}]]')


class v2vPaginatorPane(View):
    """ Represents Paginator Pane for V2V."""

    ROOT = './/form[contains(@class,"content-view-pf-pagination")]'

    items_on_page = v2vPaginationDropup('id', 'pagination-row-dropdown')
    paginator = v2vPaginator()


# Views
class InfraMappingWizardCommon(View):

    add_mapping = Button('Add Mapping')
    remove_mapping = Button('Remove Selected')
    remove_all_mappings = Button('Remove All')
    mappings_tree = InfraMappingTreeView(tree_class='treeview')


class InfraMappingForm(View):
    # common footer buttons for first 3 pages
    back_btn = Button('Back')
    next_btn = Button('Next')
    save = Button('Save')
    cancel_btn = Button('Cancel')

    def after_fill(self, was_change):
        # Cancel button is the common button on all pages so
        # waiting for footer buttons to display
        self.cancel_btn.wait_displayed()
        if self.next_btn.is_displayed:
            self.next_btn.click()
        elif self.save.is_displayed:
            self.save.click()


class InfraMappingWizardGeneralView(InfraMappingForm):
    name = TextInput(name='name')
    description = TextInput(name='description')
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
    source_clusters = MultiSelectList('source_clusters')
    target_clusters = MultiSelectList('target_clusters')

    @property
    def is_displayed(self):
        return (self.source_clusters.is_displayed and self.target_clusters.is_displayed and
        (len(self.browser.elements(".//div[contains(@class,'spinner')]")) == 0))

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
        for mapping in (values.get('mappings', []) if isinstance(values, dict) else []):
            self.source_clusters.fill(mapping['sources'])
            self.target_clusters.fill(mapping['target'])
            self.add_mapping.click()
        was_change = not self.mappings_tree.is_empty
        self.after_fill(was_change)
        return was_change


class InfraMappingWizardDatastoresView(InfraMappingForm):
    include_buttons_set2 = View.include(InfraMappingWizardCommon)
    source_datastores = MultiSelectList('source_datastores')
    target_datastores = MultiSelectList('target_datastores')
    cluster_selector = BootstrapSelect(id='cluster_select')

    @property
    def is_displayed(self):
        return (self.source_datastores.is_displayed and self.target_datastores.is_displayed and
                (len(self.browser.elements(".//div[contains(@class,'spinner')]")) == 0))

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
        for cluster in (values if isinstance(values, dict) else []):
            if self.cluster_selector.is_displayed:
                self.cluster_selector.fill(cluster)
            for mapping in values[cluster]['mappings']:
                self.source_datastores.fill(mapping['sources'])
                self.target_datastores.fill(mapping['target'])
                self.add_mapping.click()
        was_change = not self.mappings_tree.is_empty
        self.after_fill(was_change)
        return was_change


class InfraMappingWizardNetworksView(InfraMappingForm):
    include_buttons_set2 = View.include(InfraMappingWizardCommon)
    source_networks = MultiSelectList('source_networks')
    target_networks = MultiSelectList('target_networks')
    next_btn = Button("Create")  # overriding, since 'Next' is called 'Create' in this form
    cluster_selector = BootstrapSelect(id='cluster_select')

    @property
    def is_displayed(self):
        return (self.source_networks.is_displayed and self.target_networks.is_displayed and
                (len(self.browser.elements(".//div[contains(@class,'spinner')]")) == 0))

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
        for cluster in (values if isinstance(values, dict) else []):
            if self.cluster_selector.is_displayed:
                self.cluster_selector.fill(cluster)
            for mapping in values[cluster]['mappings']:
                self.source_networks.fill(mapping['sources'])
                self.target_networks.fill(mapping['target'])
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
            self.result.close.click()


# Widget for migration selection dropdown
class MigrationDropdown(Dropdown):
    """Represents the migration plan dropdown of v2v.

    Args:
        text: Text of the button, can be inner text or the title attribute.
    """
    ROOT = './/div[contains(@class, "dropdown") and .//button[contains(@id, "dropdown-filter")]]'
    BUTTON_LOCATOR = './/button[contains(@id, "dropdown-filter")]'
    ITEMS_LOCATOR = './/ul[contains(@aria-labelledby,"dropdown-filter")]/li/a'
    ITEM_LOCATOR = './/ul[contains(@aria-labelledby,"dropdown-filter")]/li/a[normalize-space(.)={}]'


class MigrationDashboardView(BaseLoggedInPage):
    create_infrastructure_mapping = Text(locator='(//a|//button)'
                                                 '[text()="Create Infrastructure Mapping"]')
    create_migration_plan = Text(locator='(//a|//button)[text()="Create Migration Plan"]')
    configure_providers = Text(locator='//a[text()="Configure Providers"]')
    migration_plans_not_started_list = MigrationPlansList("plans-not-started-list")
    migration_plans_completed_list = MigrationPlansList("plans-complete-list")
    migration_plans_archived_list = MigrationPlansList("plans-complete-list")
    sort_type_dropdown = SelectorDropdown('id', 'sortTypeMenu')
    sort_direction = Text(locator=".//span[contains(@class,'sort-direction')]")
    # TODO: XPATH requested to devel (repo:miq_v2v_ui_plugin issues:415)
    progress_card = MigrationProgressBar(locator='.//div[3]/div/div[3]/div[3]/div/div')
    not_started_plans = MigrationDashboardStatusCard(name="Not Started")
    in_progress_plans = MigrationDashboardStatusCard(name="In Progress")
    completed_plans = MigrationDashboardStatusCard(name="Complete")
    archived_plans = MigrationDashboardStatusCard(name="Archived")
    # TODO: next 3 lines are specialized only for 510z and inheritance for DashboardView59z
    # is incorrect. Need to fix it.
    paginator_view = View.include(v2vPaginatorPane, use_parent=True)
    search_box = TextInput(locator=".//div[contains(@class,'input-group')]/input")
    clear_filters = Text(".//a[text()='Clear All Filters']")
    breadcrumb = BreadCrumb()

    @property
    def is_displayed(self):
        return (self.breadcrumb.active_location == 'Migration' and
                self.navigation.currently_selected == ['Compute', 'Migration', 'Migration Plans'])

    def switch_to(self, section):
        """Switches to Not Started, In Progress, Complete or Archived Plans section."""
        sections = {
            'Not Started Plans': self.not_started_plans,
            'In Progress Plans': self.in_progress_plans,
            'Completed Plans': self.completed_plans,
            'Archived Plans': self.archived_plans
        }
        self.logger.info("Switching to Migration Dashboard section: %s", section)
        sections[section].click()

    def plan_in_progress(self, plan_name):
        """MIQ V2V UI is going through redesign as OSP will be integrated.

            # TODO: This also means that mappings/plans may be moved to different pages. Once all of
            that is settled we will need to refactor and also account for notifications.
        """
        try:
            try:
                is_plan_visible = self.progress_card.is_plan_visible(plan_name)
            except ItemNotFound:
                # This will end the wait_for loop and check the plan under completed_plans section
                return True
            if is_plan_visible:
                # log current status
                # uncomment following logs after @Yadnyawalk updates the widget for in progress card
                # logger.info("For plan %s, current migrated size is %s out of total size %s",
                #     migration_plan.name, view.progress_card.get_migrated_size(plan_name),
                #     view.progress_card.get_total_size(migration_plan.name))
                # logger.info("For plan %s, current migrated VMs are %s out of total VMs %s",
                #     migration_plan.name, view.progress_card.migrated_vms(migration_plan.name),
                #     view.progress_card.total_vm_to_be_migrated(migration_plan.name))
                try:
                    plan_time_elapsed = self.progress_card.get_clock(plan_name)
                    new_msg = "time elapsed for migration: {time}".format(time=plan_time_elapsed)
                except NoSuchElementException:
                    new_msg = "playbook is executing.."
                    pass
                self.logger.info(
                    "For plan {plan_name}, is plan in progress: {visibility}, {message}".format(
                        plan_name=plan_name,
                        visibility=is_plan_visible,
                        message=new_msg)
                )
            # return False if plan visible under "In Progress Plans"
            return not is_plan_visible
        except StaleElementReferenceException:
            self.browser.refresh()
            self.switch_to("In Progress Plans")
            return False


class MigrationDashboardView59z(MigrationDashboardView):
    """Dashboard for 59z has infra_mapping_list while 510z moves it to a separate page.
    Hence, Inheritance."""
    infra_mapping_list = InfraMappingList("infra-mappings-list-view")
    migr_dropdown = MigrationDropdown(text="Not Started Plans")

    @property
    def is_displayed(self):
        return (self.navigation.currently_selected == ['Compute', 'Migration'] and
            (len(self.browser.elements(".//div[contains(@class,'spinner')]")) == 0) and
            (len(self.browser.elements('.//div[contains(@class,"card-pf")]')) > 0))

    def switch_to(self, section):
        """Switches to Not Started, In Progress, Complete or Archived Plans section."""
        self.logger.info("Switching to Migration Dashboard section: %s", section)
        self.migr_dropdown.item_select(section)


class InfrastructureMappingView(BaseLoggedInPage):
    """This is an entire separate page, with many elements similar to what we had in
    MigrationPlanRequestDetailsView , so re-using some of those Paginator things
    by renaming those from v2vPaginator to v2vPaginator, etc."""

    infra_mapping_list = InfraMappingList("infra-mappings-list-view")
    create_infrastructure_mapping = Text(locator='(//a|//button)'
                                                 '[text()="Create Infrastructure Mapping"]')
    configure_providers = Text(locator='//a[text()="Configure Providers"]')
    paginator_view = View.include(v2vPaginatorPane, use_parent=True)
    search_box = TextInput(locator=".//div[contains(@class,'input-group')]/input")
    clear_filters = Text(".//a[text()='Clear All Filters']")
    # Used for Ascending/Descending sort
    sort_order = Text(".//button[./span[contains(@class,'sort-direction')]]")
    # Used to select filter_by 'Name' or 'Description'
    filter_by_dropdown = SelectorDropdown('id', 'filterFieldTypeMenu')
    # USed to select sort by options like 'Name', 'Number of Associated Plans'
    sort_by_dropdown = SelectorDropdown('id', 'sortTypeMenu')

    @property
    def is_displayed(self):
        # TODO: Resmove 1st condition, once /manageiq-v2v/issues/768 fix is backported to 510z
        return ((self.navigation.currently_selected ==
            ['Compute', 'Migration', 'Migration Plans'] or self.navigation.currently_selected ==
            ['Compute', 'Migration', 'Infrastructure Mappings']) and
            len(self.browser.elements(".//div[contains(@class,'spinner')]")) == 0 and
            (self.create_infrastructure_mapping.is_displayed or
                self.infra_mapping_list.is_displayed or self.configure_providers.is_displayed))


class AddInfrastructureMappingView(View):
    form = InfraMappingWizard()
    form_title_text = VersionPicker({
        Version.lowest(): 'Infrastructure Mapping Wizard',
        '5.10': 'Create Infrastructure Mapping'
    })

    @property
    def is_displayed(self):
        return self.form.title.text == self.form_title_text


class EditInfrastructureMappingView(View):
    form = InfraMappingWizard()
    form_title_text = 'Edit Infrastructure Mapping'

    @property
    def is_displayed(self):
        return self.form.title.text == self.form_title_text


class AddMigrationPlanView(View):
    title = Text(locator='.//h4[contains(@class,"modal-title")]')
    name = TextInput(name='name')
    description = TextInput(name='description')
    back_btn = Button('Back')
    # Since next is a keyword, suffixing it with btn and other two
    # because want to keep it consistent
    next_btn = Button('Next')
    cancel_btn = Button('Cancel')
    form_title_text = VersionPicker({
        Version.lowest(): 'Migration Plan Wizard',
        '5.10': 'Create Migration Plan'
    })

    @View.nested
    class general(View):  # noqa
        infra_map = BootstrapSelect('infrastructure_mapping')
        name = TextInput(name='name')
        name_help_text = Text(locator='.//div[contains(@id,"name")]/span')
        description = TextInput(name='description')
        select_vm = RadioGroup('.//div[contains(@id,"vm_choice_radio")]')

        @property
        def is_displayed(self):
            return self.infra_map.is_displayed and self.name.is_displayed

    @View.nested
    class vms(View):  # noqa
        import_btn = Button('Import')
        importcsv = Button('Import CSV')
        hidden_field = HiddenFileInput(locator='.//input[contains(@accept,".csv")]')
        # TODO: Replace string keys by integer keys after row indexing issue get fixed
        # TODO: Replace Text by Button or GenericLocatorWidget after button text get added
        table = Table('.//div[contains(@class, "container-fluid")]/table', column_widgets={
            'Select': Checkbox(locator=".//input"),
            1: Text('.//span/button[contains(@class,"btn btn-link")]')})
        filter_by_dropdown = SelectorDropdown('id', 'filterFieldTypeMenu')
        search_box = TextInput(locator='.//div[contains(@class, "modal-content")]'
            '//div[contains(@class,"input-group")]/input')
        clear_filters = Text(".//a[text()='Clear All Filters']")
        error_text = Text('.//h3[contains(@class,"blank-slate-pf-main-action") and '
                          'contains(text(), "Error:")]')
        error_icon = Text(locator='.//span[contains(@class, "pficon-error-circle-o")]')
        popover_text = Text(locator='.//div[contains(@class, "popover-content")]')

        @property
        def is_displayed(self):
            return (self.table.is_displayed and
                 (len(self.browser.elements(".//div[contains(@class,'spinner')]")) == 0))

        def filter_by_name(self, vm_name):
            try:
                # remove `if` cond https://github.com/ManageIQ/manageiq-v2v/issues/771 fixed
                if self.browser.appliance.version < '5.10':  # Don't remove nxt line, remove `if`
                    self.filter_by_dropdown.item_select("VM Name")  # just unindent
            except NoSuchElementException:
                self.logger.info("`VM Name` not present in filter dropdown!")
            self.search_box.fill(vm_name)
            self.browser.send_keys(Keys.ENTER, self.search_box)

        def filter_by_source_cluster(self, cluster_name):
            try:
                self.filter_by_dropdown.item_select("Source Cluster")
            except NoSuchElementException:
                self.logger.info("`Source Cluster` not present in filter dropdown!")
            self.search_box.fill(cluster_name)
            self.browser.send_keys(Keys.ENTER, self.search_box)

        def filter_by_path(self, path):
            try:
                self.filter_by_dropdown.item_select("Path")
            except NoSuchElementException:
                self.logger.info("`Path` not present in filter dropdown!")
            self.search_box.fill(path)
            self.browser.send_keys(Keys.ENTER, self.search_box)

        def select_by_name(self, vm_name):
            self.filter_by_name(vm_name)
            vms_selected = []
            for row in self.table.rows():
                if vm_name in row.read()['VM Name']:
                    row.select.fill(True)
                    vms_selected.append(row.read()['VM Name'])
            return vms_selected

    @View.nested
    class advanced(View):  # noqa
        pre_playbook = BootstrapSelect('preMigrationPlaybook')
        post_playbook = BootstrapSelect('postMigrationPlaybook')
        pre_checkbox = Text(locator='.//input[contains(@id, "pre_migration_select_all")]')
        post_checkbox = Text(locator='.//input[contains(@id, "post_migration_select_all")]')

    @View.nested
    class options(View):  # noqa
        create = Button('Create')
        run_migration = RadioGroup('.//div[contains(@id,"migration_plan_choice_radio")]')

        @property
        def is_displayed(self):
            return self.run_migration.is_displayed

    @View.nested
    class results(View):  # noqa
        close = Button('Close')
        msg = Text('.//h3[contains(@id,"migration-plan-results-message")]')

    @property
    def is_displayed(self):
        return self.title.text == self.form_title_text


class MigrationPlanRequestDetailsView(View):
    migration_request_details_list = MigrationPlanRequestDetailsList("plan-request-details-list")
    sort_type = SelectorDropdown('id', 'sortTypeMenu')
    paginator_view = View.include(v2vPaginatorPane, use_parent=True)
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
        self.filter_by_vm_name(vm_name)
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

    def plan_in_progress(self, vms_count=5):
        """Reuturn True or False, depending on migration plan status.

        If none of the VM migrations are in progress, return True.
        """
        if vms_count > 5:
            self.items_on_page.item_select("15")
        migration_plan_in_progress_tracker = []
        vms = self.migration_request_details_list.read()
        for vm in vms:
            clock_reading1 = self.migration_request_details_list.get_clock(vm)
            time.sleep(1)  # wait 1 sec to see if clock is ticking
            self.logger.info("For vm %s, current message is %s", vm,
                self.migration_request_details_list.get_message_text(vm))
            self.logger.info("For vm %s, current progress description is %s", vm,
                self.migration_request_details_list.get_progress_description(vm))
            clock_reading2 = self.migration_request_details_list.get_clock(vm)
            self.logger.info("clock_reading1: %s, clock_reading2:%s", clock_reading1,
                clock_reading2)
            self.logger.info("For vm %s, is currently in progress: %s", vm,
              self.migration_request_details_list.is_in_progress(vm))
            migration_plan_in_progress_tracker.append(
                self.migration_request_details_list.is_in_progress(vm) and (
                    clock_reading1 < clock_reading2))
        return not any(migration_plan_in_progress_tracker)


class MigrationSettingsView(BaseLoggedInPage):
    title = Text('//div[contains(@class, "migration-settings")]/h2')
    max_limit = Stepper(locator='//div[contains(@class, "bootstrap-touchspin-injected")]')
    apply_btn = Button('Apply')

    @property
    def is_displayed(self):
        return (self.navigation.currently_selected == ['Compute', 'Migration', 'Migration Settings']
                and self.title.text == 'Concurrent Migrations')


# Collections Entities


@attr.s
class InfrastructureMapping(BaseEntity, Updateable):
    """Class representing v2v infrastructure mappings"""
    name = attr.ib()
    description = attr.ib(default=None)
    form_data = attr.ib(default=None)

    def update(self, updates):
        view = navigate_to(self, 'Edit', wait_for_view=20)
        view.form.fill(updates)


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

    def find_mapping(self, mapping):
        view = navigate_to(self, 'All')
        if not self.appliance.version < '5.10':  # means 5.10+ or upstream
            view.items_on_page.item_select('15')
            if mapping.name in view.infra_mapping_list.read():
                return True
            # TODO: Remove While loop. It is a DIRTY HACK for now, to be addressed in PR 8075
            # =========================================================
            while not view.clear_filters.is_displayed:
                view.search_box.fill("{}\n\n".format(mapping.name))
            # =========================================================
        return mapping.name in view.infra_mapping_list.read()

    def delete(self, mapping):
        view = navigate_to(self, 'All', wait_for_view=20)
        self.find_mapping(mapping)
        mapping_list = view.infra_mapping_list
        mapping_list.delete_mapping(mapping.name)


@attr.s
class MigrationPlan(BaseEntity):
    """Class representing v2v Migration Plan"""
    name = attr.ib()


@attr.s
class MigrationPlanCollection(BaseCollection):
    """Collection object for migration plan object"""
    ENTITY = MigrationPlan

    def create(self, name, infra_map, vm_list, description=None, csv_import=False,
               pre_playbook=None, post_playbook=None, start_migration=False):
        """Create new migration plan in UI
        Args:
            name: (string) plan name
            description: (string) plan description
            infra_map: (object) infra map object name
            vm_list: (list) list of vm objects
            csv_import: (bool) flag for importing vms
            pre_playbook: (string) pre-migration playbook name
            post_playbook: (string) post-migration playbook name
            start_migration: (bool) flag for start migration
        """
        view = navigate_to(self, 'Add')
        view.general.fill({
            'infra_map': infra_map,
            'name': name,
            'description': description
        })

        if csv_import:
            view.general.select_vm.select("Import a CSV file with a list of VMs to be migrated")
            view.next_btn.click()
            temp_file = tempfile.NamedTemporaryFile(suffix='.csv')
            with open(temp_file.name, 'w') as file:
                headers = ['Name', 'Provider']
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()
                for vm in vm_list:
                    writer.writerow({'Name': vm.name, 'Provider': vm.provider.name})
            view.vms.hidden_field.fill(temp_file.name)
        else:
            view.next_btn.click()
        view.vms.wait_displayed()

        for vm in vm_list:
            view.vms.filter_by_name(vm.name)
            for row in view.vms.table.rows():
                if vm.name in row.vm_name.read():
                    row[0].fill(True)
            view.vms.clear_filters.click()
        view.next_btn.click()

        if pre_playbook:
            view.advanced.pre_playbook.wait_displayed("5s")
            view.advanced.pre_playbook.fill(pre_playbook)
            view.advanced.pre_checkbox.click()
        if post_playbook:
            view.advanced.post_playbook.wait_displayed("5s")
            view.advanced.post_playbook.fill(post_playbook)
            view.advanced.post_checkbox.click()
        view.next_btn.click()

        if start_migration:
            view.options.run_migration.select("Start migration immediately")
        view.options.create.click()
        wait_for(lambda: view.results.msg.is_displayed, timeout=60, message='Wait for Results view')

        base_flash = "Migration Plan: '{}'".format(name)
        if start_migration:
            base_flash = "{} is in progress".format(base_flash)
        else:
            base_flash = "{} has been saved".format(base_flash)
        assert view.results.msg.text == base_flash
        view.results.close.click()
        return self.instantiate(name)

    def find_completed_plan(self, migration_plan):
        """Uses search box to find migration plan, return True if found.
        Args:
            migration_plan: (object) Migration Plan object
        """
        view = navigate_to(self, 'All')
        view.switch_to("Completed Plans")
        if not self.appliance.version < '5.10':  # means 5.10+ or upstream
            view.items_on_page.item_select('15')
            if migration_plan.name in view.migration_plans_completed_list.read():
                return True
        # TODO: Next while loop is dirty hack to avoid page refresh/resetter. Need to fix it.
        # ==================================================================================
            while not view.clear_filters.is_displayed:
                view.switch_to("Completed Plans")
                view.search_box.fill("{}\n\n".format(migration_plan.name))
        # ==================================================================================
        return migration_plan.name in view.migration_plans_completed_list.read()

# Navigations


@navigator.register(InfrastructureMappingCollection, 'All')
class AllMappings(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = VersionPicker({
        Version.lowest(): MigrationDashboardView59z,
        '5.10': InfrastructureMappingView
    })

    def step(self):
        if self.obj.appliance.version < '5.10':
            self.prerequisite_view.navigation.select('Compute', 'Migration')
        else:
            self.prerequisite_view.navigation.select(
                'Compute', 'Migration', 'Infrastructure Mappings')


@navigator.register(InfrastructureMappingCollection, 'Add')
class AddInfrastructureMapping(CFMENavigateStep):
    VIEW = AddInfrastructureMappingView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.wait_displayed()
        self.prerequisite_view.create_infrastructure_mapping.click()


@navigator.register(InfrastructureMapping, 'Edit')
class EditInfrastructureMapping(CFMENavigateStep):
    VIEW = EditInfrastructureMappingView

    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        if not self.prerequisite_view.infra_mapping_list.edit_mapping(self.obj.name):
            raise ItemNotFound("Mapping {} not found".format(self.obj.name))


@navigator.register(MigrationPlanCollection, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = VersionPicker({
        Version.lowest(): MigrationDashboardView59z,
        '5.10': MigrationDashboardView
    })

    def step(self):
        if self.obj.appliance.version < '5.10':
            self.prerequisite_view.navigation.select('Compute', 'Migration')
        else:
            self.prerequisite_view.navigation.select('Compute', 'Migration', 'Migration Plans')


@navigator.register(MigrationPlanCollection, 'Add')
class AddMigrationPlan(CFMENavigateStep):
    VIEW = AddMigrationPlanView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.wait_displayed()
        self.prerequisite_view.create_migration_plan.click()


@navigator.register(MigrationPlanCollection, 'Details')
class MigrationPlanRequestDetails(CFMENavigateStep):
    VIEW = MigrationPlanRequestDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        try:
            self.prerequisite_view.migration_plans_not_started_list.select_plan(
                self.obj.ENTITY.name)
        except NoSuchElementException:
            try:
                self.prerequisite_view.migration_plans_completed_list.select_plan(
                    self.obj.ENTITY.name)
            except NoSuchElementException:
                self.prerequisite_view.progress_card.select_plan(self.obj.ENTITY.name)


@navigator.register(InfrastructureMapping, 'MigrationSettings')
class MigrationSettings(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')
    VIEW = MigrationSettingsView

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Migration', 'Migration Settings')
