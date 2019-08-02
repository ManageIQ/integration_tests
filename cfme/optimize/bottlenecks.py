# -*- coding: utf-8 -*-
import attr
from navmazing import NavigateToAttribute
from widgetastic.widget import Checkbox
from widgetastic.widget import Table
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect

from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.optimize import BottlenecksView
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import TimelinesChart
from widgetastic_manageiq import WaitTab


class BottlenecksTabsView(BottlenecksView):
    title = Text("#explorer_title_text")

    # TODO: add chart widget
    @property
    def is_displayed(self):
        region_number = self.browser.appliance.server.zone.region.number
        return (
            super(BottlenecksView, self).is_displayed and
            self.title.text == 'Region "Region {}" Bottlenecks Summary'.format(region_number) and
            self.bottlenecks.is_opened and
            self.bottlenecks.tree.currently_selected == ["Region {}".format(region_number)]
        )

    @View.nested
    class summary(WaitTab):    # noqa
        TAB_NAME = 'Summary'
        event_groups = BootstrapSelect('tl_summ_fl_grp1')
        show_host_events = Checkbox(locator='//input[@name="tl_summ_hosts"]')
        time_zone = BootstrapSelect("tl_summ_tz")
        chart = TimelinesChart(locator='//div/*[@class="timeline-pf-chart"]')

    @View.nested
    class report(WaitTab):     # noqa
        TAB_NAME = 'Report'
        event_details = Table("//div[@id='bottlenecks_report_div']/table")
        event_groups = BootstrapSelect('tl_report_fl_grp1')
        show_host_events = Checkbox(locator='//input[@name="tl_report_hosts"]')
        time_zone = BootstrapSelect("tl_report_tz")


@attr.s
class Bottlenecks(BaseEntity):

    name = attr.ib()

    @property
    def _row(self):
        view = navigate_to(self.parent, 'All')
        row = view.report.event_details.row(name=self.name)
        return row

    @property
    def time_stamp(self):
        return self._row.time_stamp.text

    @property
    def type(self):
        return self._row.type.text

    @property
    def event_type(self):
        return self._row.event_type.text

    @property
    def severity(self):
        return self._row.severity.text

    @property
    def message(self):
        return self._row.message.text


@attr.s
class BottlenecksCollection(BaseCollection):
    ENTITY = Bottlenecks

    def all(self):
        event_type = self.filters.get('event_type')
        view = navigate_to(self, 'All')
        if event_type:
            rows = view.report.event_details.rows(event_type=event_type)
        else:
            rows = view.report.event_details.rows()
        return [self.instantiate(name=row.name.text) for row in rows]


@navigator.register(BottlenecksCollection, 'All')
class All(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'Bottlenecks')

    VIEW = BottlenecksTabsView

    def resetter(self, *args, **kwargs):
        """ Set values to default """
        self.view.report.event_groups.fill('<ALL>')
        self.view.report.show_host_events.fill(False)
        self.view.report.time_zone.fill('(GMT+00:00) UTC')
        self.view.summary.event_groups.fill('<ALL>')
        self.view.summary.show_host_events.fill(False)
        self.view.summary.time_zone.fill('(GMT+00:00) UTC')
