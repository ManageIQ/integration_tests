import attr
import csv
import tempfile
import time
from selenium.common.exceptions import StaleElementReferenceException

from navmazing import NavigateToAttribute, NavigateToSibling
from selenium.webdriver.common.keys import Keys
from widgetastic.exceptions import NoSuchElementException
from widgetastic.widget import Checkbox, View, ConditionalSwitchableView
from widgetastic_manageiq import (
    HiddenFileInput,
    InfraMappingList,
    MigrationPlansList,
    MigrationProgressBar,
    MigrationPlanRequestDetailsList,
    MigrationDashboardStatusCard,
    MigrationDropdown,
    RadioGroup,
    Table,
    V2vPaginatorPane,
)
from widgetastic_patternfly import Button, BootstrapSelect, Text, TextInput, SelectorDropdown

from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.log import logger
from cfme.utils.version import Version, VersionPicker
from cfme.utils.wait import wait_for

from . import MigrationView


class DashboardCards(View):
    not_started_plans = MigrationDashboardStatusCard("Not Started")
    in_progress_plans = MigrationDashboardStatusCard("In Progress")
    completed_plans = MigrationDashboardStatusCard("Complete")
    archived_plans = MigrationDashboardStatusCard("Archived")
    archived_plans = VersionPicker(
        {
            Version.lowest(): MigrationDashboardStatusCard("Infrastructure Mappings"),
            "5.10": MigrationDashboardStatusCard("Archived"),
        }
    )

    def read(self):
        return [c.read().get("name") for c in self.sub_widgets if c.is_active].pop()


class MigrationPlanView(MigrationView):
    dashboard_cards = View.nested(DashboardCards)
    plans_list = ConditionalSwitchableView(reference="dashboard_cards")
    paginator_view = View.include(V2vPaginatorPane, use_parent=True)
    title = Text('.//div[contains(@class, "pull-left")]//h3')
    create_migration_plan = Text(locator='(//a|//button)[text()="Create Migration Plan"]')
    configure_providers = Text(locator='//a[text()="Configure Providers"]')
    sort_type_dropdown = SelectorDropdown("id", "sortTypeMenu")
    sort_direction = Text(locator=".//span[contains(@class,'sort-direction')]")
    progress_card = MigrationProgressBar(locator=".//div[3]/div/div[3]/div[3]/div/div")
    # 5.9 fields
    migr_dropdown = MigrationDropdown(text="Not Started Plans")
    infra_mapping_list = InfraMappingList("infra-mappings-list-view")
    create_infra_mapping = Text(locator='(//a|//button)[text()="Create Infrastructure Mapping"]')

    @property
    def in_migration_plan(self):
        return (
            len(self.browser.elements('.//div[contains(@class,"card-pf")]')) > 0
            and len(self.browser.elements(".//div[contains(@class,'pficon-warning-triangle-o')]"))
            < 1
        )

    @property
    def is_displayed(self):
        return self.in_migration_plan


class NotStartedPlansView(MigrationPlanView):
    TITLE = "Not Started"
    migration_plans_not_started_list = MigrationPlansList("plans-not-started-list")

    @property
    def is_displayed(self):
        in_view = VersionPicker(
            {
                Version.lowest(): (
                    self.in_migration_plan and self.migration_plans_not_started_list.is_displayed
                ),
                "5.10": self.in_migration_plan and self.TITLE in self.title.read(),
            }
        )
        return in_view


class InProgressPlansView(MigrationPlanView):
    TITLE = "In Progress"
    progress_card = MigrationProgressBar(locator=".//div[3]/div/div[3]/div[3]/div/div")

    @property
    def is_displayed(self):
        in_view = VersionPicker(
            {
                Version.lowest(): (self.in_migration_plan and self.progress_card.is_displayed),
                "5.10": self.in_migration_plan and self.TITLE in self.title.read(),
            }
        )
        return in_view


class CompletedPlansView(MigrationPlanView):
    TITLE = "Completed"
    migration_plans_completed_list = MigrationPlansList("plans-complete-list")

    @property
    def is_displayed(self):
        in_view = VersionPicker(
            {
                Version.lowest(): (
                    self.in_migration_plan and self.migration_plans_completed_list.is_displayed
                ),
                "5.10": self.in_migration_plan and self.TITLE in self.title.read(),
            }
        )
        return in_view


class ArchivedPlansView(MigrationPlanView):
    TITLE = "Archived"
    migration_plans_list = MigrationPlansList("plans-archived-list")

    @property
    def is_displayed(self):
        in_view = VersionPicker(
            {
                Version.lowest(): (
                    self.in_migration_plan and self.migration_plans_list.is_displayed
                ),
                "5.10": self.in_migration_plan and self.TITLE in self.title.read(),
            }
        )
        return in_view


class AddMigrationPlanView(View):
    title = Text(locator='.//h4[contains(@class,"modal-title")]')
    name = TextInput(name="name")
    description = TextInput(name="description")
    back_btn = Button("Back")
    next_btn = Button("Next")
    cancel_btn = Button("Cancel")
    form_title_text = VersionPicker(
        {Version.lowest(): "Migration Plan Wizard", "5.10": "Create Migration Plan"}
    )

    @View.nested
    class general(View):  # noqa
        infra_map = BootstrapSelect("infrastructure_mapping")
        name = TextInput(name="name")
        name_help_text = Text(locator='.//div[contains(@id,"name")]/span')
        description = TextInput(name="description")
        select_vm = RadioGroup('.//div[contains(@id,"vm_choice_radio")]')

        @property
        def is_displayed(self):
            return self.infra_map.is_displayed and self.name.is_displayed

    @View.nested
    class vms(View):  # noqa
        import_btn = Button("Import")
        importcsv = Button("Import CSV")
        hidden_field = HiddenFileInput(locator='.//input[contains(@accept,".csv")]')
        # TODO: Replace string keys by integer keys after row indexing issue get fixed
        # TODO: Replace Text by Button or GenericLocatorWidget after button text get added
        table = Table(
            './/div[contains(@class, "container-fluid")]/table',
            column_widgets={
                "Select": Checkbox(locator=".//input"),
                1: Text('.//span/button[contains(@class,"btn btn-link")]'),
            },
        )
        filter_by_dropdown = SelectorDropdown("id", "filterFieldTypeMenu_vms_step")
        search_box = TextInput(
            locator='.//div[contains(@class, "modal-content")]'
            '//div[contains(@class,"input-group")]/input'
        )
        clear_filters = Text(".//a[text()='Clear All Filters']")
        error_text = Text(
            './/h3[contains(@class,"blank-slate-pf-main-action") and '
            'contains(text(), "Error:")]'
        )
        error_icon = Text(locator='.//span[contains(@class, "pficon-error-circle-o")]')
        popover_text = Text(locator='.//div[contains(@class, "popover-content")]')

        @property
        def is_displayed(self):
            return self.table.is_displayed and (
                len(self.browser.elements(".//div[contains(@class,'spinner')]")) == 0
            )

        def filter_by_name(self, vm_name):
            try:
                self.filter_by_dropdown.item_select("VM Name")
            except NoSuchElementException:
                logger.info("`VM Name` not present in filter dropdown!")
            self.search_box.fill(vm_name)
            self.browser.send_keys(Keys.ENTER, self.search_box)

        def filter_by_source_cluster(self, cluster_name):
            try:
                self.filter_by_dropdown.item_select("Source Cluster")
            except NoSuchElementException:
                logger.info("`Source Cluster` not present in filter dropdown!")
            self.search_box.fill(cluster_name)
            self.browser.send_keys(Keys.ENTER, self.search_box)

        def filter_by_path(self, path):
            try:
                self.filter_by_dropdown.item_select("Path")
            except NoSuchElementException:
                logger.info("`Path` not present in filter dropdown!")
            self.search_box.fill(path)
            self.browser.send_keys(Keys.ENTER, self.search_box)

        def select_by_name(self, vm_name):
            self.filter_by_name(vm_name)
            vms_selected = []
            for row in self.table.rows():
                if vm_name in row.read()["VM Name"]:
                    row.select.fill(True)
                    vms_selected.append(row.read()["VM Name"])
            return vms_selected

    @View.nested
    class advanced(View):  # noqa
        pre_playbook = BootstrapSelect("preMigrationPlaybook")
        post_playbook = BootstrapSelect("postMigrationPlaybook")
        pre_checkbox = Text(locator='.//input[contains(@id, "pre_migration_select_all")]')
        post_checkbox = Text(locator='.//input[contains(@id, "post_migration_select_all")]')

    @View.nested
    class options(View):  # noqa
        create = Button("Create")
        run_migration = RadioGroup('.//div[contains(@id,"migration_plan_choice_radio")]')

        @property
        def is_displayed(self):
            return self.run_migration.is_displayed

    @View.nested
    class results(View):  # noqa
        close = Button("Close")
        msg = Text('.//h3[contains(@id,"migration-plan-results-message")]')

    @property
    def is_displayed(self):
        return self.title.text == self.form_title_text


class MigrationPlanRequestDetailsView(View):
    migration_request_details_list = MigrationPlanRequestDetailsList("plan-request-details-list")
    sort_type = SelectorDropdown("id", "sortTypeMenu")
    paginator_view = View.include(V2vPaginatorPane, use_parent=True)
    search_box = TextInput(locator=".//div[contains(@class,'input-group')]/input")
    clear_filters = Text(".//a[text()='Clear All Filters']")
    sort_order = Text(".//button[./span[contains(@class,'sort-direction')]]")
    filter_by_dropdown = SelectorDropdown("id", "filterFieldTypeMenu")
    filter_by_status_dropdown = SelectorDropdown("id", "filterCategoryMenu")
    sort_by_dropdown = SelectorDropdown("id", "sortTypeMenu")

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
            logger.info(
                "filter_by_dropdown not present, "
                "migration plan may not have started yet.Ignoring."
            )
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
            logger.info("Clear Filters button not present, ignoring.")
        self.filter_by_vm_name(vm_name)
        status = {
            "Message": self.migration_request_details_list.get_message_text(vm_name),
            "Description": self.migration_request_details_list.get_progress_description(vm_name),
            "Time Elapsed": self.migration_request_details_list.get_clock(vm_name),
        }
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
            raise ItemNotFound(
                "Migration plan is in Not Started State,"
                " hence filter status dropdown not visible"
            )

    def sort_by(self, option):
        """Sort VM list by using one of the 'Started','VM Name' or 'Status' option.

        Args:
            status(str): Takes status string as arg.
        """
        try:
            self.sort_by_dropdown.item_select(option)
        except NoSuchElementException:
            raise ItemNotFound(
                "Migration plan is in Not Started State," " hence sort_by dropdown not visible"
            )

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
            logger.info(
                "For vm %s, current message is %s",
                vm,
                self.migration_request_details_list.get_message_text(vm),
            )
            logger.info(
                "For vm %s, current progress description is %s",
                vm,
                self.migration_request_details_list.get_progress_description(vm),
            )
            clock_reading2 = self.migration_request_details_list.get_clock(vm)
            logger.info("clock_reading1: %s, clock_reading2:%s", clock_reading1, clock_reading2)
            logger.info(
                "For vm %s, is currently in progress: %s",
                vm,
                self.migration_request_details_list.is_in_progress(vm),
            )
            migration_plan_in_progress_tracker.append(
                self.migration_request_details_list.is_in_progress(vm)
                and (clock_reading1 < clock_reading2)
            )
        return not any(migration_plan_in_progress_tracker)


@attr.s
class MigrationPlan(BaseEntity):
    """Class representing v2v Migration Plan"""

    name = attr.ib()

    def is_plan_started(self, name):
        view = navigate_to(self, "In Progress")
        return wait_for(
            func=view.progress_card.is_plan_started,
            func_args=[name],
            message="migration plan is starting, be patient please",
            delay=5,
            num_sec=150,
            handle_exception=True,
            fail_cond=False
        )

    def is_plan_in_progress(self, name):
        """MIQ V2V UI is going through redesign as OSP will be integrated."""
        view = navigate_to(self, "In Progress")

        def _in_progress():
            try:
                try:
                    is_plan_visible = view.progress_card.is_plan_visible(name)
                    if is_plan_visible:
                        try:
                            plan_time_elapsed = view.progress_card.get_clock(name)
                            new_msg = "time elapsed for migration: {time}".format(
                                time=plan_time_elapsed)
                        except NoSuchElementException:
                            new_msg = "playbook is executing.."
                            pass
                        logger.info(
                            "For plan {plan_name}, is plan in progress: {visibility},"
                            " {message}".format(plan_name=name, visibility=is_plan_visible,
                                                message=new_msg)
                        )
                    # return False if plan visible under "In Progress Plans"
                    return not is_plan_visible
                except ItemNotFound:
                    # This will end the wait_for loop
                    # and check the plan under completed_plans section
                    return True
            except StaleElementReferenceException:
                self.browser.refresh()
                return False

        return wait_for(
            func=_in_progress,
            message="migration plan is in progress, be patient please",
            delay=5,
            num_sec=1800,
        )

    def is_migration_complete(self, name):
        """Uses search box to find migration plan, return True if found.
        Args:
            migration_plan name: (object) Migration Plan name
        """
        view = navigate_to(self, "Complete")
        view.wait_displayed()
        if self.appliance.version >= "5.10":
            view.items_on_page.item_select("15")
            if name in view.migration_plans_completed_list.read():
                return True
            # TODO: Next while loop is dirty hack to avoid page refresh/resetter. Need to fix it.
            # ==================================================================================
            while not view.clear_filters.is_displayed:
                view = navigate_to(self, "Complete")
                view.search_box.fill("{}\n\n".format(name))
            # ==================================================================================
        return (name in view.migration_plans_completed_list.read() and
                view.migration_plans_completed_list.is_plan_succeeded(name))

    def is_plan_request_shows_vm(self, name):
        view = navigate_to(self, "In Progress")
        view.progress_card.select_plan(name)
        request_view = self.create_view(MigrationPlanRequestDetailsView)
        request_view.wait_displayed()
        request_details_list = request_view.migration_request_details_list
        vms = request_details_list.read()

        def _is_migration_started():
            for vm in vms:
                if request_details_list.get_message_text(vm) != "Migrating":
                    return False
            return True

        return (
            len(vms) > 0
            and _is_migration_started
            and request_details_list.is_successful(vms[0])
            and not request_details_list.is_errored(vms[0])
        )


@attr.s
class MigrationPlanCollection(BaseCollection):
    """Collection object for migration plan object"""

    ENTITY = MigrationPlan

    def create(
        self,
        name,
        infra_map,
        vm_list,
        description=None,
        csv_import=False,
        pre_playbook=None,
        post_playbook=None,
        start_migration=False,
    ):
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
        view = navigate_to(self, "Add")
        view.general.fill({"infra_map": infra_map, "name": name, "description": description})

        if csv_import:
            view.general.select_vm.select("Import a CSV file with a list of VMs to be migrated")
            view.next_btn.click()
            temp_file = tempfile.NamedTemporaryFile(suffix=".csv")
            with open(temp_file.name, "w") as file:
                headers = ["Name", "Provider"]
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()
                for vm in vm_list:
                    writer.writerow({"Name": vm.name, "Provider": vm.provider.name})
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
        wait_for(
            lambda: view.results.msg.is_displayed, timeout=60, message="Wait for Results view"
        )

        base_flash = "Migration Plan: '{}'".format(name)
        if start_migration:
            base_flash = "{} is in progress".format(base_flash)
        else:
            base_flash = "{} has been saved".format(base_flash)
        assert view.results.msg.text == base_flash
        view.results.close.click()
        return self.instantiate(name)


@navigator.register(MigrationPlanCollection, "All")
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")
    VIEW = MigrationPlanView

    def step(self):
        if self.obj.appliance.version < "5.10":
            self.prerequisite_view.navigation.select("Compute", "Migration")
        else:
            self.prerequisite_view.navigation.select("Compute", "Migration", "Migration Plans")


@navigator.register(MigrationPlanCollection, "Add")
class AddMigrationPlan(CFMENavigateStep):
    VIEW = AddMigrationPlanView
    prerequisite = NavigateToSibling("All")

    def step(self):
        self.prerequisite_view.wait_displayed()
        self.prerequisite_view.create_migration_plan.click()


@navigator.register(MigrationPlan, "Not Started")
class NotStartedPlans(CFMENavigateStep):
    prerequisite = NavigateToAttribute("parent", "All")

    VIEW = NotStartedPlansView

    def step(self):
        if self.obj.appliance.version < "5.10":
            self.prerequisite_view.migr_dropdown.item_select("Not Started Plans")
        else:
            self.prerequisite_view.dashboard_cards.not_started_plans.click()


@navigator.register(MigrationPlan, "In Progress")
class InProgressPlans(CFMENavigateStep):
    prerequisite = NavigateToAttribute("parent", "All")

    VIEW = InProgressPlansView

    def step(self):
        if self.obj.appliance.version < "5.10":
            self.prerequisite_view.migr_dropdown.item_select("In Progress Plans")
        else:
            self.prerequisite_view.dashboard_cards.in_progress_plans.click()


@navigator.register(MigrationPlan, "Complete")
class CompletedPlans(CFMENavigateStep):
    prerequisite = NavigateToAttribute("parent", "All")

    VIEW = CompletedPlansView

    def step(self):
        if self.obj.appliance.version < "5.10":
            self.prerequisite_view.migr_dropdown.item_select("Completed Plans")
        else:
            self.prerequisite_view.dashboard_cards.completed_plans.click()


@navigator.register(MigrationPlan, "Archived")
class ArchivedPlans(CFMENavigateStep):
    prerequisite = NavigateToAttribute("parent", "All")

    VIEW = ArchivedPlansView

    def step(self):
        if self.obj.appliance.version < "5.10":
            self.prerequisite_view.migr_dropdown.item_select("Archived Plans")
        else:
            self.prerequisite_view.dashboard_cards.archived_plans.click()


@navigator.register(MigrationPlan, "Details")
class MigrationPlanRequestDetails(CFMENavigateStep):
    VIEW = MigrationPlanRequestDetailsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self):
        self.prerequisite_view.progress_card.select_plan(self.obj.name)
