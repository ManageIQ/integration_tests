# -*- coding: utf-8 -*-
"""Page model for Cloud Intel / Reports / Dashboard Widgets / RSS Feeds"""
import attr
from widgetastic.widget import TextInput
from widgetastic_patternfly import BootstrapSelect

from cfme.intelligence.reports.widgets import BaseDashboardReportWidget
from cfme.intelligence.reports.widgets import BaseDashboardWidgetFormCommon
from cfme.intelligence.reports.widgets import BaseEditDashboardWidgetStep
from cfme.intelligence.reports.widgets import BaseEditDashboardWidgetView
from cfme.intelligence.reports.widgets import BaseNewDashboardWidgetStep
from cfme.intelligence.reports.widgets import BaseNewDashboardWidgetView
from cfme.utils.appliance.implementations.ui import navigator
from widgetastic_manageiq import Calendar


class RSSWidgetFormCommon(BaseDashboardWidgetFormCommon):
    # RSS Feed Options
    type = BootstrapSelect("feed_type")
    url = BootstrapSelect("rss_feed")
    external = TextInput("txt_url")
    rows = BootstrapSelect("row_count")
    # Timer
    run = BootstrapSelect("timer_typ")
    every = BootstrapSelect("timer_hours")
    time_zone = BootstrapSelect("time_zone")
    starting_date = Calendar("miq_date_1")
    starting_hour = BootstrapSelect("start_hour")
    starting_minute = BootstrapSelect("start_min")


class NewRSSWidgetView(BaseNewDashboardWidgetView, RSSWidgetFormCommon):
    pass


class EditRSSWidgetView(BaseEditDashboardWidgetView, RSSWidgetFormCommon):
    pass


@attr.s
class RSSFeedWidget(BaseDashboardReportWidget):

    TYPE = "RSS Feeds"
    TITLE = "RSS Feed"
    pretty_attrs = ["title", "description", "type", "feed", "visibility"]
    type = attr.ib(default=None)
    feed = attr.ib(default=None)
    external = attr.ib(default=None)
    rows = attr.ib(default=None)
    timer = attr.ib(default=attr.Factory(dict))

    @property
    def fill_dict(self):
        return {
            "widget_title": self.title,
            "description": self.description,
            "active": self.active,
            "type": self.type,
            "url": self.feed,
            "external": self.external,
            "rows": self.rows,
            "run": self.timer.get("run"),
            "every": self.timer.get("hours"),
            "time_zone": self.timer.get("time_zone"),
            "starting_date": self.timer.get("starting_date"),
            "starting_hour": self.timer.get("starting_hour"),
            "starting_minute": self.timer.get("starting_minute"),
            "visibility": self.visibility
        }


@navigator.register(RSSFeedWidget, "Add")
class NewRSSWidget(BaseNewDashboardWidgetStep):
    VIEW = NewRSSWidgetView


@navigator.register(RSSFeedWidget, "Edit")
class EditRSSWidget(BaseEditDashboardWidgetStep):
    VIEW = EditRSSWidgetView
