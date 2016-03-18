# -*- coding: utf-8 -*-
"""Module handling Dashboards accordion.
"""
from cfme.fixtures import pytest_selenium as sel
from cfme.intelligence.reports.ui_elements import (
    DashboardWidgetSelector, NewerDashboardWidgetSelector)
from cfme.web_ui import Form, accordion, fill, flash, form_buttons, toolbar, Input
from cfme.web_ui.menu import nav
from utils import version
from utils.update import Updateable
from utils.pretty import Pretty


def go_to_default_func(_):
    """This can change, because the title of the default dashboard is mutable. However, we can xpath
    there quite reliable, so we use it that way we extract the name from the tree directly.
    """
    t = "//li[@id='db_xx-1' or @id='dashboards_xx-1']/span/a"
    accordion.click("Dashboards")
    accordion.tree("Dashboards", "All Dashboards", sel.text(t).encode("utf-8"))

nav.add_branch(
    "reports",
    {
        "reports_default_dashboard":
        [
            go_to_default_func,
            {
                "reports_default_dashboard_edit":
                lambda _: toolbar.select("Configuration", "Edit this Dashboard")
            }
        ],

        "reports_dashboards":
        [
            lambda ctx: accordion.tree("Dashboards", "All Dashboards", "All Groups", ctx["group"]),
            {
                "reports_dashboard_add":
                lambda _: toolbar.select("Configuration", "Add a new Dashboard")
            }
        ],

        "reports_dashboard":
        [
            lambda ctx:
            accordion.tree(
                "Dashboards", "All Dashboards", "All Groups",
                ctx["dashboard"].group, ctx["dashboard"].name
            ),
            {
                "reports_dashboard_edit":
                lambda _: toolbar.select("Configuration", "Edit this Dashboard"),
            }
        ],
    }
)


class Dashboard(Updateable, Pretty):
    form = Form(fields=[
        ("name", Input("name")),
        ("title", Input("description")),
        ("locked", Input("locked")),
        ("widgets", {
            version.LOWEST: DashboardWidgetSelector("//div[@id='form_widgets_div']"),
            "5.5": NewerDashboardWidgetSelector("//div[@id='form_widgets_div']")}),
    ])
    pretty_attrs = ['name', 'group', 'title', 'widgets']

    def __init__(self, name, group, title=None, locked=None, widgets=None):
        self.name = name
        self.title = title
        self.locked = locked
        self.widgets = widgets
        self._group = group

    @property
    def group(self):
        return self._group

    def create(self, cancel=False):
        sel.force_navigate("reports_dashboard_add", context={"group": self._group})
        fill(
            self.form,
            {k: v for k, v in self.__dict__.iteritems() if not k.startswith("_")},  # non-private
            action=form_buttons.cancel if cancel else form_buttons.add
        )
        flash.assert_no_errors()

    def update(self, updates):
        sel.force_navigate("reports_dashboard_edit", context={"dashboard": self})
        fill(self.form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        sel.force_navigate("reports_dashboard", context={"dashboard": self})
        toolbar.select(
            "Configuration", "Delete this Dashboard from the Database", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()


class DefaultDashboard(Updateable, Pretty):
    form = Form(fields=[
        ("title", Input("description")),
        ("locked", Input("locked")),
        ("widgets", {
            version.LOWEST: DashboardWidgetSelector("//div[@id='form_widgets_div']"),
            "5.5": NewerDashboardWidgetSelector("//div[@id='form_widgets_div']")}),
    ])
    reset_button = "//*[@title='Reset Dashboard Widgets to the defaults']"
    pretty_attrs = ['title', 'widgets']

    def __init__(self, title=None, locked=None, widgets=None):
        self.locked = locked
        self.widgets = widgets

    def update(self, updates):
        sel.force_navigate("reports_default_dashboard_edit")
        fill(self.form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        sel.force_navigate("reports_default_dashboard")
        toolbar.select(
            "Configuration", "Delete this Dashboard from the Database", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()

    @classmethod
    def reset_widgets(cls, cancel=False):
        sel.force_navigate("dashboard")
        sel.click(cls.reset_button, wait_ajax=False)
        sel.handle_alert(cancel)
        flash.assert_no_errors()
