# -*- coding: utf-8 -*-
"""Module handling Dashboards accordion.
"""
from navmazing import NavigateToSibling, NavigateToObject

from cfme.base import Server
from cfme.fixtures import pytest_selenium as sel
from cfme.intelligence.reports.ui_elements import NewerDashboardWidgetSelector
from cfme.web_ui import Form, accordion, fill, flash, form_buttons, toolbar, Input
from utils import version
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from utils.update import Updateable
from utils.pretty import Pretty
from . import Report


class Dashboard(Updateable, Pretty, Navigatable):
    form = Form(fields=[
        ("name", Input("name")),
        ("title", Input("description")),
        ("locked", Input("locked")),
        ("widgets", NewerDashboardWidgetSelector("//div[@id='form_widgets_div']")),
    ])
    pretty_attrs = ['name', 'group', 'title', 'widgets']

    def __init__(self, name, group, title=None, locked=None, widgets=None, appliance=None):
        Navigatable.__init__(self, appliance)
        self.name = name
        self.title = title
        self.locked = locked
        self.widgets = widgets
        self._group = group

    @property
    def group(self):
        return self._group

    def create(self, cancel=False):
        navigate_to(self, 'Add')
        fill(
            self.form,
            {k: v for k, v in self.__dict__.iteritems() if not k.startswith("_")},  # non-private
            action=form_buttons.cancel if cancel else form_buttons.add
        )
        flash.assert_no_errors()

    def update(self, updates):
        navigate_to(self, 'Edit')
        fill(self.form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        navigate_to(self, 'Details')
        toolbar.select(
            "Configuration", "Delete this Dashboard from the Database", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()


class DefaultDashboard(Updateable, Pretty, Navigatable):
    form = Form(fields=[
        ("title", Input("description")),
        ("locked", Input("locked")),
        ("widgets", NewerDashboardWidgetSelector("//div[@id='form_widgets_div']")),
    ])
    reset_button = "//*[@title='Reset Dashboard Widgets to the defaults']"
    pretty_attrs = ['title', 'widgets']

    def __init__(self, title=None, locked=None, widgets=None, appliance=None):
        Navigatable.__init__(self, appliance)
        self.title = title
        self.locked = locked
        self.widgets = widgets

    def update(self, updates):
        navigate_to(self, 'Edit')
        fill(self.form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        navigate_to(self, 'Details')
        toolbar.select(
            "Configuration", "Delete this Dashboard from the Database", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_no_errors()

    @classmethod
    def reset_widgets(cls, cancel=False):
        navigate_to(Server, 'Dashboard')
        sel.click(cls.reset_button, wait_ajax=False)
        sel.handle_alert(cancel)
        flash.assert_no_errors()


@navigator.register(DefaultDashboard, 'All')
@navigator.register(Dashboard, 'All')
class DashboardAll(CFMENavigateStep):
    prerequisite = NavigateToObject(Report, 'Dashboards')


@navigator.register(Dashboard, 'Add')
class DashboardNew(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Dashboards", "All Dashboards", "All Groups", self.obj.group)
        toolbar.select("Configuration", "Add a new Dashboard")
        sel.wait_for_element(Dashboard.form.name)


@navigator.register(Dashboard, 'Details')
class DashboardDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        accordion.tree("Dashboards", "All Dashboards", "All Groups", self.obj.group, self.obj.name)


@navigator.register(Dashboard, 'Edit')
class DashboardEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        toolbar.select("Configuration", "Edit this Dashboard")


@navigator.register(DefaultDashboard, 'Details')
class DefaultDashboardDetails(CFMENavigateStep):
    prerequisite = NavigateToSibling('All')

    def step(self):
        """This can change, because the title of the default dashboard is mutable. However, we can
        xpath there quite reliable, so we use it that way we extract the name from the tree directly
        """''
        t = version.pick({
            "5.6": "//li[@id='db_xx-1' or @id='dashboards_xx-1']/span/a",
            "5.7": "//li[@data-nodeid='0.0.0' and @class = 'list-group-item node-db_treebox']"})
        accordion.tree("Dashboards", "All Dashboards", sel.text(t).encode("utf-8"))


@navigator.register(DefaultDashboard, 'Edit')
class DefaultDashboardEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        toolbar.select("Configuration", "Edit this Dashboard")
