# -*- coding: utf-8 -*-
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text, Checkbox, Table, View, Select
from widgetastic_patternfly import Tab
from fixtures.pytest_store import store
from utils.update import Updateable
from utils.pretty import Pretty
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep

from . import BottlenecksView


class BottlenecksView(BottlenecksView):
    title = Text("#explorer_title_text")

    # TODO: add chart widget
    @property
    def is_displayed(self):
        return (
            super(BottlenecksView, self).is_displayed and
            self.title.text == 'Region "Region {}" Bottlenecks Summary'
            .format(store.current_appliance.server_region()) and
            self.bottlenecks.is_opened and
            self.bottlenecks.tree.currently_selected == ["Bottlenecks"])

    @View.nested
    class summary(Tab):    # noqa
        TAB_NAME = 'Summary'
        event_groups = Select(locator="//select[@name='tl_summ_fl_grp1']")
        show_host_events = Checkbox(locator='//input[@name="tl_summ_hosts"]')
        time_zone = Select(locator='//select[@name="tl_summ_tz"]')

    @View.nested
    class report(Tab):     # noqa
        TAB_NAME = 'Report'
        event_details = Table("//div[@id='bottlenecks_report_div']/table")
        event_groups = Select(locator="//select[@name='tl_report_fl_grp1']")
        show_host_events = Checkbox(locator='//input[@name="tl_report_hosts"]')
        time_zone = Select(locator='//select[@name="tl_report_tz"]')


class Bottlenecks(Updateable, Pretty, Navigatable):
    def __init__(self, appliance=None):
        Navigatable.__init__(self, appliance)

    def bottlenecks_db_events(self):
        tbl = self.appliance.db['bottleneck_events']
        query = self.appliance.db.session.query(tbl.timestamp,
                    tbl.resource_type, tbl.resource_name, tbl.event_type, tbl.severity, tbl.message)
        return query


@navigator.register(Bottlenecks, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    VIEW = BottlenecksView

    def step(self):
        self.parent_view.navigation.select("Optimize", "Bottlenecks")

    def am_i_here(self, *args, **kwargs):
        return self.view.is_displayed


@navigator.register(Bottlenecks, 'AllSummary')
class AllSummary(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    VIEW = BottlenecksView

    def step(self):
        self.view.summary.select()

    def am_i_here(self, *args, **kwargs):
        return self.view.is_displayed and self.view.summary.selected


@navigator.register(Bottlenecks, 'AllReport')
class AllReport(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    VIEW = BottlenecksView

    def step(self):
        self.view.report.select()

    def am_i_here(self, *args, **kwargs):
        return self.view.is_displayed and self.view.report.selected
