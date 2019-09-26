import csv
import tempfile
import time

import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import WaitFillViewStrategy
from widgetastic.widget import Checkbox
from widgetastic.widget import Select
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown
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
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for
from widgetastic_manageiq import HiddenFileInput
from widgetastic_manageiq import MigrationDashboardStatusCard
from widgetastic_manageiq import MigrationPlanRequestDetailsList
from widgetastic_manageiq import MigrationPlansList
from widgetastic_manageiq import MigrationProgressBar
from widgetastic_manageiq import RadioGroup
from widgetastic_manageiq import SearchBox
from widgetastic_manageiq import Table
from widgetastic_manageiq import V2VPaginatorPane


class MigrationView(BaseLoggedInPage):

    @property
    def in_explorer(self):
        nav_menu = (
            ["Compute", "Migration", "Migration Plans"]
            if self.context["object"].appliance.version < "5.11"
            else ["Migration", "Migration Plans"]
        )
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
    search_box = SearchBox(locator=".//div[contains(@class,'input-group')]/input")
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
    close_btn = Button("Close")
    fill_strategy = WaitFillViewStrategy("15s")

    def after_fill(self, was_change):
        self.close_btn.click()

    @property
    def is_displayed(self):
        return self.title.text == "Create Migration Plan"

    @View.nested
    class general(View):  # noqa
        infra_map = BootstrapSelect("infrastructure_mapping")
        name = TextInput(name="name")
        name_help_text = Text(locator='.//div[contains(@id,"name")]/span')
        description = TextInput(name="description")
        choose_vm = RadioGroup('.//div[contains(@id,"vm_choice_radio")]')
        alert = Text('.//div[contains(@class, "alert")]')
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
        clear_filters = Text(".//a[text()='Clear All Filters']")
        error_text = Text('.//h3[contains(@class,"blank-slate-pf-main-action") and '
                          'contains(text(), "Error:")]')
        popover_text = Text(locator='.//div[contains(@class, "popover-content")]')
        table = Table(
            './/div[contains(@class, "container-fluid")]/table',
            column_widgets={
                "Select": Checkbox(locator=".//input"),
                1: Text('.//span/button[contains(@class,"btn btn-link")]'),
            },
        )
        search_box = SearchBox(
            locator='.//div[contains(@class, "modal-content")]'
                    '//div[contains(@class,"input-group")]/input'
        )

        @property
        def is_displayed(self):
            return self.table.is_displayed and (
                len(self.browser.elements(".//div[contains(@class,'spinner')]")) == 0
            )

        def csv_import(self, vm_list):
            """
            Vm's can be imported using csv for migration.
            Opens a temporary csv with Columns Name and Provider
            and fill it with vm's from vm_list to be used in fill
            Args:
                vm_list: list of vm's to be imported through csv
            """
            temp_file = tempfile.NamedTemporaryFile(suffix=".csv")
            with open(temp_file.name, "w") as file:
                headers = ["Name", "Provider"]
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()
                for vm in vm_list:
                    writer.writerow({"Name": vm.name, "Provider": vm.provider.name})
            self.hidden_field.fill(temp_file.name)

        def fill(self, values):
            """
            If importing Vm's from csv file , use the file created in csv_import method.
            Search Vm using searchbox.
            Select checkbox(row[0]) of all the Vm's imported in the table
            Args:
                 values : List of Vm's
            """
            csv_import = values.get('csv_import')
            vm_list = values.get('vm_list')
            if csv_import:
                self.csv_import(vm_list)
            for vm in vm_list:
                self.search_box.fill(vm.name)
                for row in self.table.rows():
                    if vm.name in row.vm_name.read():
                        # select checkbox
                        row[0].fill(True)
                    self.clear_filters.click()
            was_change = True
            self.after_fill(was_change)
            return was_change

        def after_fill(self, was_change):
            self.parent.next_btn.click()

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
            """
            This is required only for OSP
            and only if we want to edit osp_security_group or osp_flavor
            otherwise not needed.
            If none them is to be edited only next needs to be clicked.
            Args:
                values:
            """
            was_change = True
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
            self.after_fill(was_change)
            return was_change

        def after_fill(self, was_change):
            self.parent.next_btn.click()

    @View.nested
    class advanced(View):  # noqa
        pre_playbook = BootstrapSelect("preMigrationPlaybook")
        post_playbook = BootstrapSelect("postMigrationPlaybook")
        pre_checkbox = Checkbox(locator='.//input[contains(@id, "pre_migration_select_all")]')
        post_checkbox = Checkbox(locator='.//input[contains(@id, "post_migration_select_all")]')

        @property
        def is_displayed(self):
            return self.pre_playbook.is_displayed

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
            was_change = True
            self.run_migration.select(values)
            self.after_fill(was_change)
            return was_change

        def after_fill(self, was_change):
            self.create.click()

    @View.nested
    class results(View):  # noqa
        msg = Text('.//h3[contains(@id,"migration-plan-results-message")]')

        @property
        def is_displayed(self):
            return self.msg.is_displayed


class MigrationPlanRequestDetailsView(View):
    migration_request_details_list = MigrationPlanRequestDetailsList("plan-request-details-list")
    paginator_view = View.include(V2VPaginatorPane, use_parent=True)
    download_logs = Dropdown("Download Log")

    @property
    def is_displayed(self):
        return self.migration_request_details_list.is_displayed

    def plan_in_progress(self):
        """Return True or False, depending on migration plan status.
        If none of the VM migrations are in progress, return True.
        """
        self.items_on_page.item_select("15")
        migration_plan_in_progress_tracker = []
        vms = self.migration_request_details_list.read()
        for vm in vms:
            clock_reading1 = self.migration_request_details_list.get_clock(vm)
            time.sleep(1)  # wait 1 sec to see if clock is ticking
            clock_reading2 = self.migration_request_details_list.get_clock(vm)
            logger.info("clock_reading1: %s, clock_reading2:%s", clock_reading1, clock_reading2)
            migration_plan_in_progress_tracker.append(
                self.migration_request_details_list.is_in_progress(vm)
                and (clock_reading1 < clock_reading2)
            )
        return not any(migration_plan_in_progress_tracker)


@attr.s
class MigrationPlan(BaseEntity):
    """Class representing v2v Migration Plan
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
            pre_checkbox: checkbox premigration playbook
            post_checkbox: post migration checkbox
            start_migration: (string) text of radio button to choose
    """

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
    pre_checkbox = attr.ib(default=False)
    post_checkbox = attr.ib(default=False)
    start_migration = attr.ib(default="Start migration immediately")

    MIGRATION_STATES = {'Started': lambda self: self.plan_started(),
                        'In_Progress': lambda self: self.in_progress(),
                        'Completed': lambda self: self.completed(),
                        'Successful': lambda self: self.successful()}

    def plan_started(self):
        """waits until the plan begins and starts showing progress time"""
        view = navigate_to(self, "InProgress")
        return wait_for(
            func=view.progress_card.is_plan_started,
            func_args=[self.name],
            message="migration plan is starting, be patient please",
            delay=5,
            num_sec=300,
            handle_exception=True
        )

    def in_progress(self):
        """
        Migration plan takes some time to complete.
        Plan is visible means migration is still in progress so we wait until
        the plan is invisible(or till migration is complete).
        """
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
                        logger.info(
                            "For plan {plan_name}, is plan in progress: {visibility}, {message}".
                            format(plan_name=self.name, visibility=is_plan_visible,
                                   message=new_msg)
                        )
                    except NoSuchElementException:
                        logger.info("For plan {plan_name} playbook is executing..".format(
                            plan_name=self.name))
                return not is_plan_visible
            except ItemNotFound:
                return True

        return wait_for(
            func=_in_progress,
            message="migration plan is in progress, be patient please",
            delay=5,
            num_sec=1800,
            fail_cond=False
        )

    def completed(self):
        """ Uses search box to find migration plan, return True if found.
            checks if plan is completed.
        """
        view = navigate_to(self, "Complete")
        return self.name in view.plans_completed_list.read()

    def successful(self):
        """ Find migration plan and checks if plan is successful."""
        view = navigate_to(self, "Complete")
        return view.plans_completed_list.is_plan_succeeded(self.name)

    def delete_not_started_plan(self):
        """ Find migration plan and delete."""
        view = navigate_to(self, "NotStarted")
        return view.plans_not_started_list.delete_plan(self.name)

    def get_plan_vm_list(self, wait_for_migration=True):
        """
        Navigates to plan details and waits for plan to complete
        returns : List of Vm's on plan details page
        """
        view = navigate_to(self, "Details")
        view.wait_displayed()
        if wait_for_migration:
            wait_for(func=view.plan_in_progress,
                    message="migration plan is in progress, be patient please",
                    delay=5, num_sec=4500)
        request_details_list = view.migration_request_details_list
        return request_details_list

    def wait_for_state(self, state):
        try:
            method = self.MIGRATION_STATES.get(state)
            if method:
                return bool(method(self))
            else:
                raise ValueError("Value {} not defined.It should be 'Started', 'In_Progress',"
                                 " 'Completed' or 'Successful'".format(state))
        except TimedOutError:
            logger.info("Wait for state :%s timed out", state)


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
        pre_checkbox=False,
        post_checkbox=False,
        start_migration=True
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
            pre_checkbox: checkbox premigration playbook
            post_checkbox: post migration checkbox
            start_migration: (bool) flag to start migration
        """
        view = navigate_to(self, "Add")

        import_btn = None
        if csv_import:
            import_btn = "Import a CSV file with a list of VMs to be migrated"
        view.general.fill({"infra_map": infra_map,
                           "name": name,
                           "description": description,
                           "csv_import": import_btn})

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
        view.advanced.wait_displayed()
        view.advanced.fill({
            'pre_playbook': pre_playbook,
            'post_playbook': post_playbook,
            'pre_checkbox': pre_checkbox,
            'post_checkbox': post_checkbox
        })

        # Schedule migration check
        view.schedule.wait_displayed()
        start_selection = ("Start migration immediately"
                           if start_migration else "Save migration plan to run later")
        view.schedule.fill(start_selection)

        return self.instantiate(
            name=name,
            infra_map=infra_map,
            vm_list=vm_list,
            description=description,
            csv_import=csv_import,
            target_provider=target_provider,
            osp_security_group=osp_security_group,
            osp_flavor=osp_flavor,
            pre_playbook=pre_playbook,
            post_playbook=post_playbook,
            pre_checkbox=pre_checkbox,
            post_checkbox=post_checkbox,
            start_migration=start_migration
        )


@navigator.register(MigrationPlanCollection, "All")
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")
    VIEW = MigrationPlanView

    def step(self):
        if self.obj.appliance.version < "5.11":
            self.prerequisite_view.navigation.select("Compute", "Migration", "Migration Plans")
        else:
            self.prerequisite_view.navigation.select("Migration", "Migration Plans")


@navigator.register(MigrationPlanCollection, "Add")
class AddMigrationPlan(CFMENavigateStep):
    VIEW = AddMigrationPlanView
    prerequisite = NavigateToSibling("All")

    def step(self):
        self.prerequisite_view.create_migration_plan.click()


@navigator.register(MigrationPlanCollection, "NotStarted")
@navigator.register(MigrationPlan, "NotStarted")
class NotStartedPlans(CFMENavigateStep):
    prerequisite = NavigateToSibling("All")

    VIEW = NotStartedPlansView

    def step(self):
        self.prerequisite_view.dashboard_cards.not_started_plans.click()


@navigator.register(MigrationPlanCollection, "InProgress")
@navigator.register(MigrationPlan, "InProgress")
class InProgressPlans(CFMENavigateStep):
    prerequisite = NavigateToAttribute("parent", "All")

    VIEW = InProgressPlansView

    def step(self):
        self.prerequisite_view.dashboard_cards.in_progress_plans.click()


@navigator.register(MigrationPlanCollection, "Complete")
@navigator.register(MigrationPlan, "Complete")
class CompletedPlans(CFMENavigateStep):
    prerequisite = NavigateToAttribute("parent", "All")

    VIEW = CompletedPlansView

    def step(self):
        self.prerequisite_view.dashboard_cards.completed_plans.click()
        self.prerequisite_view.wait_displayed()
        self.prerequisite_view.items_on_page.item_select("15")
        self.prerequisite_view.search_box.fill("{}\n\n".format(self.obj.name))


@navigator.register(MigrationPlanCollection, "Archived")
class ArchivedPlans(CFMENavigateStep):
    prerequisite = NavigateToAttribute("parent", "All")

    VIEW = ArchivedPlansView

    def step(self):
        self.prerequisite_view.dashboard_cards.archived_plans.click()


@navigator.register(MigrationPlan, 'Details')
class MigrationPlanRequestDetails(CFMENavigateStep):
    VIEW = MigrationPlanRequestDetailsView
    prerequisite = NavigateToSibling("InProgress")

    def step(self):
        self.prerequisite_view.progress_card.select_plan(self.obj.name)
