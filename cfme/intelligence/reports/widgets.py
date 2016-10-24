# -*- coding: utf-8 -*-
"""Module handling Dashboard Widgets accordion.

"""

from cfme.fixtures import pytest_selenium as sel
from cfme.intelligence.reports.ui_elements import ExternalRSSFeed, MenuShortcuts, Timer
from cfme.web_ui import (
    CheckboxSelect, Form, InfoBlock, Select, ShowingInputs, accordion, fill, toolbar, Input)
from navmazing import NavigateToAttribute, NavigateToSibling
from cfme.web_ui import flash, form_buttons, summary_title
from utils import version
from utils.update import Updateable
from utils.pretty import Pretty
from utils.wait import wait_for
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


visibility_obj = ShowingInputs(
    Select("//select[@id='visibility_typ']"),
    CheckboxSelect({
        version.LOWEST: "//td[normalize-space(.)='User Roles']/../td/table",
        "5.5": "//label[normalize-space(.)='User Roles']/../div/table"}),
    min_values=1
)


class Widget(Updateable, Pretty, Navigatable):
    TITLE = None
    DETAIL_PAGE = None
    WAIT_STATES = {"Queued", "Running"}
    status_info = InfoBlock("Status")

    def __init__(self, title, description=None, active=None, shortcuts=None, visibility=None,
                 appliance=None):
        Navigatable.__init__(self, appliance)
        self.title = title
        self.description = description
        self.active = active
        self.shortcuts = shortcuts
        self.visibility = visibility


    def generate(self, wait=True, **kwargs):
        navigate_to(self, 'Details')
        toolbar.select("Configuration", "Generate Widget content now", invokes_alert=True)
        sel.handle_alert()
        flash.assert_message_match("Content generation for this Widget has been initiated")
        flash.assert_no_errors()
        if wait:
            self.wait_generated(**kwargs)

    def wait_generated(self, timeout=600):
        wait_for(
            self.check_status,
            num_sec=timeout, delay=5, fail_condition=lambda result: result != "Complete")

    def check_status(self):
        navigate_to(self, 'Details')
        return self.status_info("Current Status").text

    @classmethod
    def detect(cls, t, *args, **kwargs):
        # Can't be in class because it does not see child classes
        MAPPING = {
            "rss_widget": RSSFeedWidget,
            "rssbox": RSSFeedWidget,
            "chart_widget": ChartWidget,
            "chartbox": ChartWidget,
            "report_widget": ReportWidget,
            "reportbox": ReportWidget,
            "menu_widget": MenuWidget,
            # TODO: menubox?
        }
        if t not in MAPPING:
            raise ValueError(t)
        return MAPPING[t](*args, **kwargs)

    def create(self, cancel=False):
        navigate_to(self, 'Add')
        fill(self.form, self.__dict__, action=form_buttons.cancel if cancel else form_buttons.add)
        flash.assert_no_errors()

    def update(self, updates):
        navigate_to(self, 'Edit')
        fill(self.form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        navigate_to(self, 'Details')
        toolbar.select("Configuration", "Delete this Widget from the Database", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()


@navigator.register(Widget, 'All')
class WidgetsAll(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Cloud Intel', 'Reports')(None)
        accordion.tree("Dashboard Widgets", "All Widgets", self.obj.TITLE)

    def am_i_here(self, *args, **kwargs):
        return summary_title() == "{} Widgets".format(self.obj.TITLE[:-1])


@navigator.register(Widget, 'Details')
class WidgetsDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Dashboard Widgets", "All Widgets", self.obj.TITLE, self.obj.title)

    def am_i_here(self, *args, **kwargs):
        return summary_title() == "{} Widget \"{}\"".format(self.obj.TITLE[:-1], self.obj.title)


@navigator.register(Widget, 'Add')
class WidgetsAdd(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        toolbar.select("Configuration", "Add a new Widget")


@navigator.register(Widget, 'Edit')
class WidgetsEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        toolbar.select("Configuration", "Edit this Widget")


class MenuWidget(Widget):
    form = Form(fields=[
        ("title", Input("title")),
        ("description", Input("description")),
        ("active", Input("enabled")),
        ("shortcuts", MenuShortcuts("add_shortcut")),
        ("visibility", visibility_obj),
    ])
    TITLE = "Menus"
    pretty_attrs = ['description', 'shortcuts', 'visibility']

    def __init__(self, title, description=None, active=None, shortcuts=None, visibility=None):
        self.title = title
        self.description = description
        self.active = active
        self.shortcuts = shortcuts
        self.visibility = visibility


class ReportWidget(Widget):
    form = Form(fields=[
        ("title", Input("title")),
        ("description", Input("description")),
        ("active", Input("enabled")),
        ("filter", ShowingInputs(
            Select("//select[@id='filter_typ']"),
            Select("//select[@id='subfilter_typ']"),
            Select("//select[@id='repfilter_typ']"),
            min_values=3
        )),  # Might be abstracted out too
        ("columns", ShowingInputs(
            Select("//select[@id='chosen_pivot1']"),
            Select("//select[@id='chosen_pivot2']"),
            Select("//select[@id='chosen_pivot3']"),
            Select("//select[@id='chosen_pivot4']"),
            min_values=1
        )),
        ("rows", Select("//select[@id='row_count']")),
        ("timer", Timer()),
        ("visibility", visibility_obj),
    ])
    TITLE = "Reports"
    pretty_attrs = ['description', 'filter', 'visibility']

    def __init__(self,
            title, description=None, active=None, filter=None, columns=None, rows=None, timer=None,
            visibility=None):
        self.title = title
        self.description = description
        self.active = active
        self.filter = filter
        self.columns = columns
        self.rows = rows
        self.timer = timer
        self.visibility = visibility


class ChartWidget(Widget):
    form = Form(fields=[
        ("title", Input("title")),
        ("description", Input("description")),
        ("active", Input("enabled")),
        ("filter", Select("//select[@id='repfilter_typ']")),
        ("timer", Timer()),
        ("visibility", visibility_obj),
    ])
    TITLE = "Charts"
    pretty_attrs = ['title', 'description', 'filter', 'visibility']

    def __init__(self,
            title, description=None, active=None, filter=None, timer=None, visibility=None):
        self.title = title
        self.description = description
        self.active = active
        self.filter = filter
        self.timer = timer
        self.visibility = visibility


class RSSFeedWidget(Widget):
    form = Form(fields=[
        ("title", Input("title")),
        ("description", Input("description")),
        ("active", Input("enabled")),
        ("type", Select("//select[@id='feed_type']")),
        ("feed", Select("//select[@id='rss_feed']")),
        ("external", ExternalRSSFeed()),
        ("rows", Select("//select[@id='row_count']")),
        ("timer", Timer()),
        ("visibility", visibility_obj),
    ])
    TITLE = "RSS Feeds"
    pretty_attrs = ['title', 'description', 'type', 'feed', 'visibility']

    def __init__(self,
            title, description=None, active=None, type=None, feed=None, external=None, rows=None,
            timer=None, visibility=None):
        self.title = title
        self.description = description
        self.active = active
        self.type = type
        self.feed = feed
        self.external = external
        self.rows = rows
        self.timer = timer
        self.visibility = visibility
