# -*- coding: utf-8 -*-
"""Page model for Cloud Intel / Reports / Dashboard Widgets / Reports"""
from widgetastic_manageiq import Calendar
from widgetastic_patternfly import BootstrapSelect

from cfme.utils.appliance.implementations.ui import navigator
from . import (
    BaseDashboardReportWidget,
    BaseDashboardWidgetFormCommon,
    BaseEditDashboardWidgetStep,
    BaseEditDashboardWidgetView,
    BaseNewDashboardWidgetStep,
    BaseNewDashboardWidgetView
)


class ReportWidgetFormCommon(BaseDashboardWidgetFormCommon):

    # Report Options
    filter = BootstrapSelect("filter_typ")
    subfilter = BootstrapSelect("subfilter_typ")
    repfilter = BootstrapSelect("repfilter_typ")
    column1 = BootstrapSelect("chosen_pivot1")
    column2 = BootstrapSelect("chosen_pivot2")
    column3 = BootstrapSelect("chosen_pivot3")
    column4 = BootstrapSelect("chosen_pivot4")
    row_count = BootstrapSelect("row_count")
    # Timer
    run = BootstrapSelect("timer_typ")
    every = BootstrapSelect("timer_hours")
    time_zone = BootstrapSelect("time_zone")
    starting_date = Calendar("miq_date_1")
    starting_hour = BootstrapSelect("start_hour")
    starting_minute = BootstrapSelect("start_min")


class NewReportWidgetView(BaseNewDashboardWidgetView, ReportWidgetFormCommon):
    pass


class EditReportWidgetView(BaseEditDashboardWidgetView, ReportWidgetFormCommon):
    pass


class ReportWidget(BaseDashboardReportWidget):

    TYPE = "Reports"
    TITLE = "Report"
    pretty_attrs = ["description", "filter", "visibility"]

    def __init__(self, title, description=None, active=None, filter=None, columns=None, rows=None,
            timer=None, visibility=None):
        self.title = title
        self.description = description
        self.active = active
        self.filter, self.subfilter, self.repfilter = filter
        for i in range(1, 5):
            try:
                setattr(self, "column{}".format(i), columns[i])
            except IndexError:
                setattr(self, "column{}".format(i), None)
        self.rows = rows
        self.timer = timer
        self.visibility = visibility

    @property
    def fill_dict(self):
        return {
            "widget_title": self.title,
            "description": self.description,
            "active": self.active,
            "filter": self.filter,
            "subfilter": self.subfilter,
            "repfilter": self.repfilter,
            "column1": self.column1,
            "column2": self.column2,
            "column3": self.column3,
            "column4": self.column4,
            "run": self.timer.get("run"),
            "every": self.timer.get("hours"),
            "time_zone": self.timer.get("time_zone"),
            "starting_date": self.timer.get("starting_date"),
            "starting_hour": self.timer.get("starting_hour"),
            "starting_minute": self.timer.get("starting_minute"),
            "rows": self.rows,
            "visibility": self.visibility
        }


@navigator.register(ReportWidget, "Add")
class NewReportWidget(BaseNewDashboardWidgetStep):
    VIEW = NewReportWidgetView


@navigator.register(ReportWidget, "Edit")
class EditReportWidget(BaseEditDashboardWidgetStep):
    VIEW = EditReportWidgetView
