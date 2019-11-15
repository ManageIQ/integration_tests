"""Page model for Cloud Intel / Reports / Dashboard Widgets / Charts"""
import attr
from widgetastic_patternfly import BootstrapSelect

from cfme.intelligence.reports.widgets import BaseDashboardReportWidget
from cfme.intelligence.reports.widgets import BaseDashboardWidgetFormCommon
from cfme.intelligence.reports.widgets import BaseEditDashboardWidgetStep
from cfme.intelligence.reports.widgets import BaseEditDashboardWidgetView
from cfme.intelligence.reports.widgets import BaseNewDashboardWidgetStep
from cfme.intelligence.reports.widgets import BaseNewDashboardWidgetView
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import Calendar


class ChartWidgetFormCommon(BaseDashboardWidgetFormCommon):
    # Chart Report
    filter = BootstrapSelect("repfilter_typ")
    # Timer
    run = BootstrapSelect("timer_typ")
    every = BootstrapSelect("timer_hours")
    time_zone = BootstrapSelect("time_zone")
    starting_date = Calendar("miq_date_1")
    starting_hour = BootstrapSelect("start_hour")
    starting_minute = BootstrapSelect("start_min")


class NewChartWidgetView(BaseNewDashboardWidgetView, ChartWidgetFormCommon):
    pass


class EditChartWidgetView(BaseEditDashboardWidgetView, ChartWidgetFormCommon):
    pass


@attr.s
class ChartWidget(BaseDashboardReportWidget):

    TYPE = "Charts"
    TITLE = "Chart"
    pretty_attrs = ["title", "description", "filter", "visibility"]
    filter = attr.ib(default=None)
    timer = attr.ib(default=attr.Factory(dict))

    @property
    def fill_dict(self):
        return {
            "widget_title": self.title,
            "description": self.description,
            "active": self.active,
            "filter": self.filter,
            "run": self.timer.get("run"),
            "every": self.timer.get("hours"),
            "time_zone": self.timer.get("time_zone"),
            "starting_date": self.timer.get("starting_date"),
            "starting_hour": self.timer.get("starting_hour"),
            "starting_minute": self.timer.get("starting_minute"),
            "visibility": self.visibility
        }


@navigator.register(ChartWidget, "Add")
class NewChartWidget(BaseNewDashboardWidgetStep):
    VIEW = NewChartWidgetView


@navigator.register(ChartWidget, "Edit")
class EditChartWidget(BaseEditDashboardWidgetStep):
    VIEW = EditChartWidgetView
