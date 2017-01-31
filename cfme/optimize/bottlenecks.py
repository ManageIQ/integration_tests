# -*- coding: utf-8 -*-
from navmazing import NavigateToAttribute
from widgetastic.widget import Text, Checkbox, Table, View
from widgetastic_patternfly import Tab, BootstrapSelect
from fixtures.pytest_store import store
from utils.update import Updateable
from utils.pretty import Pretty
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep

from . import BottlenecksView


class BottlenecksTabsView(BottlenecksView):
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
        event_groups = BootstrapSelect('tl_summ_fl_grp1')
        show_host_events = Checkbox(locator='//input[@name="tl_summ_hosts"]')
        time_zone = BootstrapSelect("tl_summ_tz")

    @View.nested
    class report(Tab):     # noqa
        TAB_NAME = 'Report'
        event_details = Table("//div[@id='bottlenecks_report_div']/table")
        event_groups = BootstrapSelect('tl_report_fl_grp1')
        show_host_events = Checkbox(locator='//input[@name="tl_report_hosts"]')
        time_zone = BootstrapSelect("tl_report_tz")


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

    VIEW = BottlenecksTabsView

    def step(self):
        self.prerequisite_view.navigation.select("Optimize", "Bottlenecks")

    def am_i_here(self, *args, **kwargs):
        return self.view.is_displayed
