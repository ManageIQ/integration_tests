# -*- coding: utf-8 -*-
"""Module handling Dashboard Widgets accordion.

"""
from __future__ import unicode_literals
from xml.sax.saxutils import quoteattr

from cfme.fixtures import pytest_selenium as sel
from cfme.intelligence.reports.ui_elements import ExternalRSSFeed, MenuShortcuts, Timer
from cfme.web_ui import (
    CheckboxSelect, Form, InfoBlock, Select, ShowingInputs, accordion, fill, toolbar, Input)
from cfme.web_ui import flash, form_buttons
from cfme.web_ui.menu import nav
from utils import version
from utils.update import Updateable
from utils.pretty import Pretty
from utils.wait import wait_for


nav.add_branch(
    "reports",
    {
        "reports_widgets_menus":
        [
            lambda _: accordion.tree("Dashboard Widgets", "All Widgets", "Menus"),
            {
                "reports_widgets_menu_add":
                lambda _: toolbar.select("Configuration", "Add a new Widget")
            }
        ],

        "reports_widgets_menu":
        [
            lambda ctx:
            accordion.tree("Dashboard Widgets", "All Widgets", "Menus", ctx["widget"].title),
            {
                "reports_widgets_menu_delete":
                lambda _: toolbar.select("Configuration", "Delete this Widget from the Database"),

                "reports_widgets_menu_edit":
                lambda _: toolbar.select("Configuration", "Edit this Widget"),
            }
        ],

        "reports_widgets_reports":
        [
            lambda _: accordion.tree("Dashboard Widgets", "All Widgets", "Reports"),
            {
                "reports_widgets_report_add":
                lambda _: toolbar.select("Configuration", "Add a new Widget")
            }
        ],

        "reports_widgets_report":
        [
            lambda ctx:
            accordion.tree("Dashboard Widgets", "All Widgets", "Reports", ctx["widget"].title),
            {
                "reports_widgets_report_delete":
                lambda _: toolbar.select("Configuration", "Delete this Widget from the Database"),

                "reports_widgets_report_edit":
                lambda _: toolbar.select("Configuration", "Edit this Widget"),
            }
        ],

        "reports_widgets_charts":
        [
            lambda _: accordion.tree("Dashboard Widgets", "All Widgets", "Charts"),
            {
                "reports_widgets_chart_add":
                lambda _: toolbar.select("Configuration", "Add a new Widget")
            }
        ],

        "reports_widgets_chart":
        [
            lambda ctx:
            accordion.tree("Dashboard Widgets", "All Widgets", "Charts", ctx["widget"].title),
            {
                "reports_widgets_chart_delete":
                lambda _: toolbar.select("Configuration", "Delete this Widget from the Database"),

                "reports_widgets_chart_edit":
                lambda _: toolbar.select("Configuration", "Edit this Widget"),
            }
        ],

        "reports_widgets_rss_feeds":
        [
            lambda _: accordion.tree("Dashboard Widgets", "All Widgets", "RSS Feeds"),
            {
                "reports_widgets_rss_feed_add":
                lambda _: toolbar.select("Configuration", "Add a new Widget")
            }
        ],

        "reports_widgets_rss_feed":
        [
            lambda ctx:
            accordion.tree("Dashboard Widgets", "All Widgets", "RSS Feeds", ctx["widget"].title),
            {
                "reports_widgets_rss_feed_delete":
                lambda _: toolbar.select("Configuration", "Delete this Widget from the Database"),

                "reports_widgets_rss_feed_edit":
                lambda _: toolbar.select("Configuration", "Edit this Widget"),
            }
        ],
    }
)


visibility_obj = ShowingInputs(
    Select("//select[@id='visibility_typ']"),
    CheckboxSelect({
        version.LOWEST: "//td[normalize-space(.)='User Roles']/../td/table",
        "5.5": "//label[normalize-space(.)='User Roles']/../div/table"}),
    min_values=1
)


class Widget(Updateable, Pretty):
    TITLE = None
    DETAIL_PAGE = None
    WAIT_STATES = {"Queued", "Running"}
    status_info = InfoBlock("Status")

    @property
    def on_widget_page(self):
        return sel.is_displayed(
            "//div[contains(@class, 'dhtmlxPolyInfoBar')]"
            "/div[contains(@class, 'dhtmlxInfoBarLabel') and normalize-space(.)={}]".format(
                quoteattr("{} Widget \"{}\"".format(self.TITLE, self.title))))

    def go_to_detail(self):
        if self.on_widget_page:
            toolbar.select("Reload current display")
        else:
            sel.force_navigate(type(self).DETAIL_PAGE, context={"widget": self})

    def generate(self, wait=True, **kwargs):
        self.go_to_detail()
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
        self.go_to_detail()
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


class MenuWidget(Widget):
    form = Form(fields=[
        ("title", Input("title")),
        ("description", Input("description")),
        ("active", Input("enabled")),
        ("shortcuts", MenuShortcuts("add_shortcut")),
        ("visibility", visibility_obj),
    ])
    TITLE = "Menu"
    pretty_attrs = ['description', 'shortcuts', 'visibility']
    DETAIL_PAGE = "reports_widgets_menu"

    def __init__(self, title, description=None, active=None, shortcuts=None, visibility=None):
        self.title = title
        self.description = description
        self.active = active
        self.shortcuts = shortcuts
        self.visibility = visibility

    def create(self, cancel=False):
        sel.force_navigate("reports_widgets_menu_add")
        fill(self.form, self.__dict__, action=form_buttons.cancel if cancel else form_buttons.add)
        flash.assert_no_errors()

    def update(self, updates):
        sel.force_navigate("reports_widgets_menu_edit", context={"widget": self})
        fill(self.form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        self.go_to_detail()
        toolbar.select("Configuration", "Delete this Widget from the Database", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()


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
    TITLE = "Report"
    pretty_attrs = ['description', 'filter', 'visibility']
    DETAIL_PAGE = "reports_widgets_report"

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

    def create(self, cancel=False):
        sel.force_navigate("reports_widgets_report_add")
        fill(self.form, self.__dict__, action=form_buttons.cancel if cancel else form_buttons.add)
        flash.assert_no_errors()

    def update(self, updates):
        sel.force_navigate("reports_widgets_report_edit", context={"widget": self})
        fill(self.form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        self.go_to_detail()
        toolbar.select("Configuration", "Delete this Widget from the Database", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()


class ChartWidget(Widget):
    form = Form(fields=[
        ("title", Input("title")),
        ("description", Input("description")),
        ("active", Input("enabled")),
        ("filter", Select("//select[@id='repfilter_typ']")),
        ("timer", Timer()),
        ("visibility", visibility_obj),
    ])
    TITLE = "Chart"
    pretty_attrs = ['title', 'description', 'filter', 'visibility']
    DETAIL_PAGE = "reports_widgets_chart"

    def __init__(self,
            title, description=None, active=None, filter=None, timer=None, visibility=None):
        self.title = title
        self.description = description
        self.active = active
        self.filter = filter
        self.timer = timer
        self.visibility = visibility

    def create(self, cancel=False):
        sel.force_navigate("reports_widgets_chart_add")
        fill(self.form, self.__dict__, action=form_buttons.cancel if cancel else form_buttons.add)
        flash.assert_no_errors()

    def update(self, updates):
        sel.force_navigate("reports_widgets_chart_edit", context={"widget": self})
        fill(self.form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        self.go_to_detail()
        toolbar.select("Configuration", "Delete this Widget from the Database", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()


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
    TITLE = "RSS Feed"
    pretty_attrs = ['title', 'description', 'type', 'feed', 'visibility']
    DETAIL_PAGE = "reports_widgets_rss_feed"

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

    def create(self, cancel=False):
        sel.force_navigate("reports_widgets_rss_feed_add")
        fill(self.form, self.__dict__, action=form_buttons.cancel if cancel else form_buttons.add)
        flash.assert_no_errors()

    def update(self, updates):
        sel.force_navigate("reports_widgets_rss_feed_edit", context={"widget": self})
        fill(self.form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        self.go_to_detail()
        toolbar.select("Configuration", "Delete this Widget from the Database", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()
