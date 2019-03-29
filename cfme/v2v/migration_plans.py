import csv
import tempfile
import time

import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from selenium.webdriver.common.keys import Keys
from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import WaitFillViewStrategy
from widgetastic.widget import Checkbox
from widgetastic.widget import Select
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import PFIcon
from widgetastic_patternfly import SelectorDropdown
from widgetastic_patternfly import Text
from widgetastic_patternfly import TextInput

from cfme.base.login import BaseLoggedInPage
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
from widgetastic_manageiq import HiddenFileInput
from widgetastic_manageiq import MigrationDashboardStatusCard
from widgetastic_manageiq import MigrationPlanRequestDetailsList
from widgetastic_manageiq import MigrationPlansList
from widgetastic_manageiq import MigrationProgressBar
from widgetastic_manageiq import RadioGroup
from widgetastic_manageiq import Table
from widgetastic_manageiq import V2VPaginatorPane


class MigrationView(BaseLoggedInPage):

    @property
    def in_explorer(self):
        nav_menu = ["Compute", "Migration", "Migration Plans"]
        return self.logged_in_as_current_user and self.navigation.currently_selected == nav_menu

    @property
    def is_displayed(self):
        return self.in_explorer


class DashboardCards(View):
    not_started_plans = MigrationDashboardStatusCard("Not Started")
    in_progress_plans = MigrationDashboardStatusCard("In Progress")
    completed_plans = MigrationDashboardStatusCard("Complete")
    archived_plans = MigrationDashboardStatusCard("Archived")

    def read(self):
        return [c.read().get("name") for c in self.sub_widgets if c.is_active]


class MigrationPlanView(MigrationView):
    dashboard_cards = View.nested(DashboardCards)
    paginator_view = View.include(V2VPaginatorPane, use_parent=True)
    title = Text('.//div[contains(@class, "pull-left")]//h3')
    create_migration_plan = Text(locator='(//a|//button)[text()="Create Migration Plan"]')
    configure_providers = Text(locator='//a[text()="Configure Providers"]')
    sort_type_dropdown = SelectorDropdown("id", "sortTypeMenu")
    sort_direction = Text(locator=".//span[contains(@class,'sort-direction')]")
    progress_card = MigrationProgressBar()
    search_box = TextInput(locator=".//div[contains(@class,'input-group')]/input")
    clear_filters = Text(".//a[text()='Clear All Filters']")

    @property
    def in_migration_plan(self):
        return (
            self.in_explorer and self.create_migration_plan.is_displayed and
            len(self.browser.elements('.//div[contains(@class,"card-pf")]')) > 0
            and len(self.browser.elements(PFIcon.icons.WARNING)) < 1
        )

    @property
    def is_displayed(self):
        return self.in_migration_plan


class NotStartedPlansView(MigrationPlanView):
    plans_not_started_list = MigrationPlansList("plans-not-started-list")

    @property
    def is_displayed(self):
        return (self.in_migration_plan and
                self.plans_not_started_list.is_displayed and
                self.title.text == 'Not Started Plans')


class InProgressPlansView(MigrationPlanView):
    progress_card = MigrationProgressBar()

    @property
    def is_displayed(self):
            return (self.in_migration_plan and
                    self.progress_card.is_displayed and
                    self.title.text == 'In Progress Plans')


class CompletedPlansView(MigrationPlanView):
    plans_completed_list = MigrationPlansList("plans-complete-list")

    @property
    def is_displayed(self):
            return (self.in_migration_plan and
                    self.plans_completed_list.is_displayed and
                    self.title.text == 'Completed Plans')


class ArchivedPlansView(MigrationPlanView):
    archived_plans_list = MigrationPlansList("plans-archived-list")

    @property
    def is_displayed(self):
            return (self.in_migration_plan and
                    self.archived_plans_list.is_displayed and
                    self.title.text == 'Archived Plans')


class AddMigrationPlanView(View):
    title = Text(locator='.//h4[contains(@class,"modal-title")]')
    back_btn = Button("Back")
    next_btn = Button("Next")
    cancel_btn = Button("Cancel")
    close = Button("Close")
    fill_strategy = WaitFillViewStrategy("15s")

    @View.nested
    class general(View):  # noqa
        infra_map = BootstrapSelect("infrastructure_mapping")
        name = TextInput(name="name")
        name_help_text = Text(locator='.//div[contains(@id,"name")]/span')
        description = TextInput(name="description")
        select_vm = RadioGroup('.//div[contains(@id,"vm_choice_radio")]')
        fill_strategy = WaitFillViewStrategy("15s")

        @property
        def is_displayed(self):
            return self.infra_map.is_displayed and self.name.is_displayed

        def after_fill(self, was_change):
            self.parent.next_btn.click()

    @View.nested
    class vms(View):  # noqa
        import_btn = Button("Import")
        hidden_field = HiddenFileInput(locator='.//input[contains(@accept,".csv")]')

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

        def csv_import(self, vm_list):
            temp_file = tempfile.NamedTemporaryFile(suffix=".csv")
            with open(temp_file.name, "w") as file:
                headers = ["Name", "Provider"]
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()
                for vm in vm_list:
                    writer.writerow({"Name": vm.name, "Provider": vm.provider.name})
            self.hidden_field.fill(temp_file.name)

        def fill(self, values):
            csv_import = values.get('csv_import')
            vm_list = values.get('vm_list')
            if csv_import:
                self.csv_import(vm_list)
            for vm in vm_list:
                self.filter("VM Name", vm.name)
                for row in self.table.rows():
                    if vm.name in row.vm_name.read():
                        row[0].fill(True)
                self.clear_filters.click()
            self.parent.next_btn.click()

        def after_fill(self, was_change):
            self.browser.send_keys(Keys.ENTER, self.search_box)

        def filter(self, type, name):
            try:
                self.filter_by_dropdown.item_select(type)
            except NoSuchElementException:
                logger.info("{} not present in filter dropdown!".format(type))
            self.search_box.fill(name)
            self.after_fill(was_change=True)

        def select_by_name(self, vm_name):
            self.filter("VM Name", vm_name)
            vms_selected = []
            for row in self.table.rows():
                if vm_name in row.read()["VM Name"]:
                    row.select.fill(True)
                    vms_selected.append(row.read()["VM Name"])
            return vms_selected

    @View.nested
    class instance_properties(View):  # noqa
        table = Table('.//div[contains(@class, "container-fluid")]/table')
        edit_instance_properties = Text(locator='.//button/span[contains(@class, "pficon-edit")]')
        select_security_group = Select(locator='.//td[5]/select')
        select_flavor = Select(locator='.//td[6]/select')
        save_properties = Text(locator='.//div[contains(@class, "inline-edit-buttons")]'
                                       '/button[contains(@aria-label, "Save")]')

        @property
        def is_displayed(self):
            return (self.table.is_displayed and
                    (len(self.browser.elements(".//div[contains(@class,'spinner')]")) == 0))

        def fill(self, values):
            osp_security_group = values.get('osp_security_group')
            osp_flavor = values.get('osp_flavor')
            if osp_security_group or osp_flavor:
                self.edit_instance_properties.click()
                self.select_security_group.wait_displayed()
                if osp_security_group:
                    self.select_security_group.fill(osp_security_group)
                if osp_flavor:
                    self.select_flavor.fill(osp_flavor)
                self.save_properties.click()
            self.after_fill(was_change=True)

        def after_fill(self, was_change):
            self.parent.next_btn.click()

    @View.nested
    class advanced(View):  # noqa
        pre_playbook = BootstrapSelect("preMigrationPlaybook")
        post_playbook = BootstrapSelect("postMigrationPlaybook")
        pre_checkbox = Text(locator='.//input[contains(@id, "pre_migration_select_all")]')
        post_checkbox = Text(locator='.//input[contains(@id, "post_migration_select_all")]')

        @property
        def is_displayed(self):
            return self.pre_playbook.is_displayed

        def fill(self, values):
            self.pre_playbook.wait_displayed("5s")
            pre_playbook = values.get('pre_playbook')
            post_playbook = values.get('post_playbook')
            if pre_playbook:
                self.pre_playbook.fill(pre_playbook)
                self.pre_checkbox.click()
            if post_playbook:
                self.post_playbook.wait_displayed("5s")
                self.post_playbook.fill(post_playbook)
                self.post_checkbox.click()
            self.after_fill(was_change=True)

        def after_fill(self, was_change):
            self.parent.next_btn.click()

    @View.nested
    class schedule(View):  # noqa
        create = Button("Create")
        run_migration = RadioGroup('.//div[contains(@id,"migration_plan_choice_radio")]')

        @property
        def is_displayed(self):
            return self.run_migration.is_displayed

        def fill(self, values):
            if values:
                self.run_migration.select("Start migration immediately")
            self.after_fill(was_change=True)

        def after_fill(self, was_change):
            self.create.click()

    @View.nested
    class results(View):  # noqa
        msg = Text('.//h3[contains(@id,"migration-plan-results-message")]')

        @property
        def is_displayed(self):
            return self.msg.is_displayed

    def after_fill(self, was_change):
        self.close.click()

    @property
    def is_displayed(self):
        return self.title.text == "Create Migration Plan"


class MigrationPlanRequestDetailsView(View):
    migration_request_details_list = MigrationPlanRequestDetailsList("plan-request-details-list")
    sort_type = SelectorDropdown("id", "sortTypeMenu")
    paginator_view = View.include(V2VPaginatorPane, use_parent=True)
    search_box = TextInput(locator=".//div[contains(@class,'input-group')]/input")
    clear_filters = Text(".//a[text()='Clear All Filters']")
    sort_order = Text(".//button[./span[contains(@class,'sort-direction')]]")
    filter_by_dropdown = SelectorDropdown("id", "filterFieldTypeMenu")
    filter_by_status_dropdown = SelectorDropdown("id", "filterCategoryMenu")

    @property
    def is_displayed(self):
        return self.migration_request_details_list.is_displayed

    def after_fill(self, was_change):
        self.browser.send_keys(Keys.ENTER, self.search_box)

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
        self.after_fill(was_change=True)

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
                         ['Pending', 'Validating', 'Pre-migration', 'Migrating',
                          'VM Transformations Ccompleted', 'VM Transformations Failed']
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
            option(str): Takes option string as arg.
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
    infra_map = attr.ib()
    vm_list = attr.ib()
    description = attr.ib(default=None)
    csv_import = attr.ib(default=False)
    target_provider = attr.ib(default=None)
    osp_security_group = attr.ib(default=None)
    osp_flavor = attr.ib(default=None)
    pre_playbook = attr.ib(default=None)
    post_playbook = attr.ib(default=None)

    def is_plan_in_progress(self):
        """MIQ V2V UI is going through redesign as OSP will be integrated."""
        view = navigate_to(self, "InProgress")

        def _in_progress():
            try:
                is_plan_visible = view.progress_card.is_plan_visible(self.name)
                if is_plan_visible:
                    try:
                        plan_time_elapsed = view.progress_card.get_clock(self.name)
                        new_msg = "time elapsed for migration: {time}".format(
                            time=plan_time_elapsed
                        )
                    except NoSuchElementException:
                        new_msg = "playbook is executing.."
                        pass
                    logger.info(
                        "For plan {plan_name}, is plan in progress: {visibility}, {message}".format(
                            plan_name=self.name, visibility=is_plan_visible, message=new_msg
                        )
                    )
                return not is_plan_visible
            except ItemNotFound:
                return True

        return wait_for(
            func=_in_progress,
            message="migration plan is in progress, be patient please",
            delay=5,
            num_sec=1800,
        )

    def is_migration_complete(self):
        """Uses search box to find migration plan, return True if found.
        Args:
            migration_plan name: (object) Migration Plan name
        """
        view = navigate_to(self, "Complete")
        view.wait_displayed()
        view.items_on_page.item_select("15")
        view.search_box.fill("{}\n\n".format(self.name))
        return (self.name in view.plans_completed_list.read() and
                view.plans_completed_list.is_plan_succeeded(self.name))

    def migration_plan_request(self):
        view = navigate_to(self, "InProgress")
        view.progress_card.select_plan(self.name)
        request_view = self.create_view(MigrationPlanRequestDetailsView, wait="10s")
        request_details_list = request_view.migration_request_details_list
        view.items_on_page.item_select("15")
        self.is_plan_in_progress()
        return request_details_list


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
        target_provider=None,
        osp_security_group=None,
        osp_flavor=None,
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
            target_provider:Target provider (OSP or RHV)
            osp_security_group: security group for OSP
            osp_flavor:Flavor for OSP,
            pre_playbook: (string) pre-migration playbook name
            post_playbook: (string) post-migration playbook name
            start_migration: (bool) flag for start migration
        """
        view = navigate_to(self, "Add")

        radio_btn = None
        if csv_import:
            radio_btn = "Import a CSV file with a list of VMs to be migrated"
        view.general.fill({"infra_map": infra_map,
                           "name": name,
                           "description": description,
                           "csv_import": radio_btn})

        view.vms.wait_displayed()
        view.vms.fill({
            'csv_import': csv_import,
            'vm_list': vm_list})

        # For OSP we need to fill this extra tab
        if target_provider:
            if target_provider.one_of(OpenStackProvider):
                view.instance_properties.wait_displayed()
                view.instance_properties.fill({
                    'osp_security_group': osp_security_group,
                    'osp_flavor': osp_flavor
                })

        view.advanced.fill({
            'pre_playbook': pre_playbook,
            'post_playbook': post_playbook
        })

        view.schedule.fill(start_migration)
        return self.instantiate(name=name, infra_map=infra_map, vm_list=vm_list)

    def is_plan_started(self, name):
        view = navigate_to(self, "All")
        return wait_for(
            func=view.progress_card.is_plan_started,
            func_args=[name],
            message="migration plan is starting, be patient please",
            delay=5,
            num_sec=150,
            handle_exception=True
        )


@navigator.register(MigrationPlanCollection, "All")
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")
    VIEW = MigrationPlanView

    def step(self):
        self.prerequisite_view.navigation.select("Compute", "Migration", "Migration Plans")


@navigator.register(MigrationPlanCollection, "Add")
class AddMigrationPlan(CFMENavigateStep):
    VIEW = AddMigrationPlanView
    prerequisite = NavigateToSibling("All")

    def step(self):
        self.prerequisite_view.create_migration_plan.click()


@navigator.register(MigrationPlan, "NotStarted")
class NotStartedPlans(CFMENavigateStep):
    prerequisite = NavigateToAttribute("parent", "All")

    VIEW = NotStartedPlansView

    def step(self):
        self.prerequisite_view.dashboard_cards.not_started_plans.click()


@navigator.register(MigrationPlan, "InProgress")
class InProgressPlans(CFMENavigateStep):
    prerequisite = NavigateToAttribute("parent", "All")

    VIEW = InProgressPlansView

    def step(self):
        self.prerequisite_view.dashboard_cards.in_progress_plans.click()


@navigator.register(MigrationPlan, "Complete")
class CompletedPlans(CFMENavigateStep):
    prerequisite = NavigateToAttribute("parent", "All")

    VIEW = CompletedPlansView

    def step(self):
        self.prerequisite_view.dashboard_cards.completed_plans.click()


@navigator.register(MigrationPlan, "Archived")
class ArchivedPlans(CFMENavigateStep):
    prerequisite = NavigateToAttribute("parent", "All")

    VIEW = ArchivedPlansView

    def step(self):
        self.prerequisite_view.dashboard_cards.archived_plans.click()
