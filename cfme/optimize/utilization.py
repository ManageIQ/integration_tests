import re

import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import Table
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import DatePicker
from widgetastic_patternfly import GroupedBarChart
from widgetastic_patternfly import LineChart

from cfme.base.ui import BaseLoggedInPage
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import ManageIQTree
from widgetastic_manageiq import WaitTab


class UtilizationTrendsView(BaseLoggedInPage):
    """Base class for header and nav check"""

    title = Text(locator='//*[@id="explorer_title"]')
    tree = ManageIQTree("treeview-utilization_tree")

    @property
    def in_utilization(self):
        return self.logged_in_as_current_user and self.navigation.currently_selected == [
            "Optimize" if self.context["object"].appliance.version < "5.11" else "Overview",
            "Utilization",
        ]


class UtilizationTrendsAllView(UtilizationTrendsView):
    @property
    def is_displayed(self):
        return self.in_utilization and self.tree.is_displayed


class SummaryOptionView(View):
    show_weeks_back = BootstrapSelect(id='summ_days')
    classification = BootstrapSelect(id='summ_tag')
    calendar = DatePicker(id='miq_date_1')


class DetailsOptionView(View):
    show_weeks_back = BootstrapSelect(id='details_days')
    classification = BootstrapSelect(id='details_tag')


class ReportOptionView(View):
    show_weeks_back = BootstrapSelect(id='report_days')
    classification = BootstrapSelect(id='report_tag')
    calendar = DatePicker(id='miq_date_2')


class DatastoreUtilizationTrendsView(UtilizationTrendsView):
    @View.nested
    class summary(WaitTab):  # noqa
        TAB_NAME = 'Summary'
        options = View.nested(SummaryOptionView)
        chart = GroupedBarChart(id='miq_chart_parent_utilts_0')
        disk_table = Table(".//tr/th[contains(text(), 'Disk')]/ancestor::table")

    @View.nested
    class details(WaitTab):  # noqa
        TAB_NAME = 'Details'
        options = View.nested(DetailsOptionView)
        disk_chart = LineChart(id="miq_chart_utiltrend_0")

    @View.nested
    class report(WaitTab):  # noqa
        TAB_NAME = 'Report'
        options = View.nested(ReportOptionView)
        disk_table = Table(".//tr/th[contains(text(), 'Disk')]/ancestor::table")

    @property
    def is_displayed(self):
        is_title_matched = bool(
            re.match(r'Datastore ".*" Utilization Trend Summary', self.title.text)
        )
        return self.in_utilization and is_title_matched


class HostUtilizationTrendsView(UtilizationTrendsView):
    @View.nested
    class summary(WaitTab):  # noqa
        TAB_NAME = 'Summary'
        options = View.nested(SummaryOptionView)
        chart = GroupedBarChart(id='miq_chart_parent_utilts_0')
        cpu_table = Table(".//tr/th[contains(text(), 'CPU')]/ancestor::table")
        memory_table = Table(".//tr/th[contains(text(), 'Memory')]/ancestor::table")

    @View.nested
    class details(WaitTab):  # noqa
        TAB_NAME = 'Details'
        options = View.nested(DetailsOptionView)
        cpu_chart = LineChart(id="miq_chart_utiltrend_0")
        memory_chart = LineChart(id="miq_chart_utiltrend_1")

    @View.nested
    class report(WaitTab):  # noqa
        TAB_NAME = 'Report'
        options = View.nested(ReportOptionView)
        cpu_table = Table(".//tr/th[contains(text(), 'CPU')]/ancestor::table")
        memory_table = Table(".//tr/th[contains(text(), 'Memory')]/ancestor::table")

    @property
    def is_displayed(self):
        is_title_matched = bool(
            re.match(r'Host / Node ".*" Utilization Trend Summary', self.title.text)
        )
        return self.in_utilization and is_title_matched


class ClusterUtilizationTrendsView(HostUtilizationTrendsView):
    @property
    def is_displayed(self):
        is_title_matched = bool(
            re.match(r'Cluster / Deployment Role ".*" Utilization Trend Summary', self.title.text)
        )
        return self.in_utilization and is_title_matched


class ProviderUtilizationTrendsView(HostUtilizationTrendsView):
    @property
    def is_displayed(self):
        is_title_matched = bool(
            re.match(r'Provider ".*" Utilization Trend Summary', self.title.text)
        )
        return self.in_utilization and is_title_matched


class RegionUtilizationTrendsView(UtilizationTrendsView):
    @View.nested
    class summary(WaitTab):  # noqa
        TAB_NAME = 'Summary'
        options = View.nested(SummaryOptionView)
        chart = GroupedBarChart(id='miq_chart_parent_utilts_0')
        cpu_table = Table(".//tr/th[contains(text(), 'CPU')]/ancestor::table")
        memory_table = Table(".//tr/th[contains(text(), 'Memory')]/ancestor::table")
        disk_table = Table(".//tr/th[contains(text(), 'Disk')]/ancestor::table")

    @View.nested
    class details(WaitTab):  # noqa
        TAB_NAME = 'Details'
        options = View.nested(DetailsOptionView)
        cpu_chart = LineChart(id="miq_chart_utiltrend_0")
        memory_chart = LineChart(id="miq_chart_utiltrend_1")
        disk_chart = LineChart(id="miq_chart_utiltrend_2")

    @View.nested
    class report(WaitTab):  # noqa
        TAB_NAME = 'Report'
        options = View.nested(ReportOptionView)
        cpu_table = Table(".//tr/th[contains(text(), 'CPU')]/ancestor::table")
        memory_table = Table(".//tr/th[contains(text(), 'Memory')]/ancestor::table")
        disk_table = Table(".//tr/th[contains(text(), 'Disk')]/ancestor::table")

    @property
    def is_displayed(self):
        is_title_matched = bool(
            re.match(r'Region ".*" Utilization Trend Summary', self.title.text)
        )
        return self.in_utilization and is_title_matched


@attr.s
class Utilization(BaseEntity):
    region = attr.ib()
    provider = attr.ib(default=None)
    cluster = attr.ib(default=None)
    host = attr.ib(default=None)
    datastore = attr.ib(default=None)

    @property
    def _region_path(self):
        return (
            [self.region.region_string]
            if self.appliance.version < "5.11"
            else ["Enterprise", self.region.region_string]
        )


@attr.s
class UtilizationCollection(BaseCollection):
    """Collection object for the :py:class:'cfme.optimize.utilization.Utilization'."""

    ENTITY = Utilization


@navigator.register(UtilizationCollection, "All")
class All(CFMENavigateStep):
    VIEW = UtilizationTrendsAllView
    prerequisite = NavigateToAttribute("appliance.server", "LoggedIn")

    def step(self, *args, **kwargs):
        nav_path = ["Optimize"] if self.appliance.version < "5.11" else ["Overview", "Utilization"]
        self.prerequisite_view.navigation.select(*nav_path)


@navigator.register(Utilization, "Region")
class RegionOptimizeUtilization(CFMENavigateStep):
    VIEW = RegionUtilizationTrendsView
    prerequisite = NavigateToAttribute("parent", "All")

    def step(self, *args, **kwargs):
        self.prerequisite_view.tree.click_path(*self.obj._region_path)


@navigator.register(Utilization, "Provider")
class ProviderOptimizeUtilization(CFMENavigateStep):
    VIEW = ProviderUtilizationTrendsView
    prerequisite = NavigateToSibling("Region")

    def step(self, *args, **kwargs):
        path = self.obj._region_path + ["Providers", self.obj.provider.name]
        self.prerequisite_view.tree.click_path(*path)


@navigator.register(Utilization, "Cluster")
class ClusterOptimizeUtilization(CFMENavigateStep):
    VIEW = ClusterUtilizationTrendsView
    prerequisite = NavigateToSibling("Region")

    def step(self, *args, **kwargs):
        path = self.obj._region_path + [
            "Providers",
            self.obj.provider.name,
            "Cluster / Deployment Role",
            self.obj.cluster.name
        ]
        self.prerequisite_view.tree.click_path(*path)


@navigator.register(Utilization, "Host")
class HostOptimizeUtilization(CFMENavigateStep):
    VIEW = HostUtilizationTrendsView
    prerequisite = NavigateToSibling("Region")

    def step(self, *args, **kwargs):
        path = self.obj._region_path + [
            "Providers",
            self.obj.provider.name,
            "Cluster / Deployment Role",
            self.obj.cluster.name,
            self.obj.host.name
        ]
        self.prerequisite_view.tree.click_path(*path)


@navigator.register(Utilization, "Datastore")
class DatastoreOptimizeUtilization(CFMENavigateStep):
    VIEW = DatastoreUtilizationTrendsView
    prerequisite = NavigateToSibling("Region")

    def step(self, *args, **kwargs):
        path = self.obj._region_path + ["Datastores", self.obj.datastore.name]
        self.prerequisite_view.tree.click_path(*path)
