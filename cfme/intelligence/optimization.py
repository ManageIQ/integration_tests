import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import Table
from widgetastic.widget import Text
from widgetastic_patternfly import Button
from widgetastic_patternfly import SelectorDropdown

from cfme.common import BaseLoggedInPage
from cfme.intelligence.reports.reports import ReportsCollection
from cfme.intelligence.reports.saved import SavedReportsCollection
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.wait import wait_for
from widgetastic_manageiq import SearchBox


class OptimizationView(BaseLoggedInPage):
    title = Text('//*[@id="main-content"]//h1')
    table = Table(
        '//*[@id="main_div"]//table', column_widgets={"Action": Button("contains", "Queue Report")}
    )
    refresh = Button(title="Refresh the list")

    @property
    def is_displayed(self):
        return (
            self.logged_in_as_current_user
            and self.title.text == "Optimization"
            and self.table.is_displayed
            and self.navigation.currently_selected == ["Overview", "Optimization"]
            and self.breadcrumb.locations == ["Overview", "Optimization"]
        )


class OptimizationReportAllView(OptimizationView):
    table = Table('//*[@id="main_div"]//table')

    @property
    def is_displayed(self):
        menu_name = self.context["object"].menu_name
        return (
            self.logged_in_as_current_user
            and self.title.text == menu_name
            and self.navigation.currently_selected == ["Overview", "Optimization"]
            and self.breadcrumb.locations == ["Overview", "Optimization", menu_name]
        )


class OptimizationSavedReportDetailsView(OptimizationView):
    field = SelectorDropdown("id", "filterFieldTypeMenu")
    search_text = SearchBox(locator='//input[contains(@placeholder, "search text")]')
    table = Table('//*[@id="main_div"]//table')

    @property
    def is_displayed(self):
        context_obj = self.context["object"]
        return (
            self.logged_in_as_current_user
            and self.title.text == context_obj.name
            and self.table.is_displayed
            and self.navigation.currently_selected == ["Overview", "Optimization"]
            and self.breadcrumb.locations
            == ["Overview", "Optimization", context_obj.parent.parent.menu_name, context_obj.name]
        )


@attr.s
class OptimizationSavedReport(BaseEntity):
    name = attr.ib()
    run_at = attr.ib()
    username = attr.ib(default=None)


@attr.s
class OptimizationSavedReportsCollection(BaseCollection):
    ENTITY = OptimizationSavedReport


@attr.s
class OptimizationReport(BaseEntity):
    menu_name = attr.ib()
    runs = attr.ib(default=None)

    _collections = {
        "optimization_saved_reports": OptimizationSavedReportsCollection,
        "saved_reports": SavedReportsCollection,
        "reports": ReportsCollection,
    }

    @property
    def last_run_at(self):
        view = navigate_to(self.parent, "All")
        return view.table.row(report_name=self.menu_name)["Last Run at"].text

    def queue(self):
        view = navigate_to(self.parent, "All")
        row = view.table.row(report_name=self.menu_name)
        row.action.widget.click()
        view.flash.assert_no_error()

        # column value for "Last Run at" changes to an empty string after `Queue report` button is
        # pressed
        wait_for(
            lambda: row["Last Run at"].text != "",
            fail_func=view.refresh.click,
            num_sec=60,
            message="Wait for report queue completion",
            delay=1,
        )
        last_run_at = row["Last Run at"].text
        row.click()

        view = self.create_view(OptimizationReportAllView)

        return self.collections.optimization_saved_reports.instantiate(
            name=view.table.row(last_run_at=last_run_at)["Report"].text,
            run_at=last_run_at,
            username=self.appliance.user.credential.principal,
        )


@attr.s
class OptimizationReportsCollection(BaseCollection):
    ENTITY = OptimizationReport


@navigator.register(OptimizationReportsCollection, "All")
class OptimizationAll(CFMENavigateStep):
    VIEW = OptimizationView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select("Overview", "Optimization")


@navigator.register(OptimizationReport, "SavedAll")
class SavedOptimizationReportAll(CFMENavigateStep):
    VIEW = OptimizationReportAllView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.table.row(report_name=self.obj.menu_name).click()


@navigator.register(OptimizationSavedReport, "Details")
class SavedOptimizationReportDetails(CFMENavigateStep):
    VIEW = OptimizationSavedReportDetailsView
    prerequisite = NavigateToAttribute("parent.parent", "SavedAll")

    def step(self, *args, **kwargs):
        self.prerequisite_view.table.row(last_run_at=self.obj.run_at).click()
