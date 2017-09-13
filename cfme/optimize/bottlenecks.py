# -*- coding: utf-8 -*-
from navmazing import NavigateToAttribute
from widgetastic.widget import Text, Checkbox, Table, View
from widgetastic_patternfly import Tab, BootstrapSelect
from widgetastic_manageiq import TimelinesChart

from cfme.utils.update import Updateable
from cfme.utils.pretty import Pretty
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep

from . import BottlenecksView


class BottlenecksTabsView(BottlenecksView):
    title = Text("#explorer_title_text")

    # TODO: add chart widget
    @property
    def is_displayed(self):
        return (
            super(BottlenecksView, self).is_displayed and
            self.title.text == 'Region "Region {}" Bottlenecks Summary'
            .format(self.browser.appliance.server_region()) and
            self.bottlenecks.is_opened and
            self.bottlenecks.tree.currently_selected == ["Bottlenecks"])

    @View.nested
    class summary(Tab):    # noqa
        TAB_NAME = 'Summary'
        event_groups = BootstrapSelect('tl_summ_fl_grp1')
        show_host_events = Checkbox(locator='//input[@name="tl_summ_hosts"]')
        time_zone = BootstrapSelect("tl_summ_tz")
        chart = TimelinesChart(locator='//div/*[@class="timeline-pf-chart"]')

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


@navigator.register(Bottlenecks, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'Bottlenecks')

    VIEW = BottlenecksTabsView

    def resetter(self):
        """ Set values to default """
        self.view.report.event_groups.fill('<ALL>')
        self.view.report.show_host_events.fill(False)
        self.view.report.time_zone.fill('(GMT+00:00) UTC')
        self.view.summary.event_groups.fill('<ALL>')
        self.view.summary.show_host_events.fill(False)
        self.view.summary.time_zone.fill('(GMT+00:00) UTC')
