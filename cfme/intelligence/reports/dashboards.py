# -*- coding: utf-8 -*-
"""Page model for Cloud Intel / Reports / Dashboards"""
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Checkbox, Text
from widgetastic_manageiq import SummaryFormItem, DashboardWidgetsPicker
from widgetastic_patternfly import Button, Input

from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from . import CloudIntelReportsView


class DashboardAllGroupsView(CloudIntelReportsView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.title.text == 'Dashboards for "{}"'.format(self.context["object"].group) and
            self.dashboards.is_opened and
            self.dashboards.tree.currently_selected == [
                "All Dashboards",
                "All Groups",
                self.context["object"].group
            ]
        )


class DashboardFormCommon(CloudIntelReportsView):
    title = Text("#explorer_title_text")
    basic_information = Text(".//div[@id='form_div']/h3")
    name = Input(name="name")
    tab_title = Input(name="description")
    locked = Checkbox("locked")
    sample_dashboard = Text(".//div[@id='form_widgets_div']/h3")
    widget_picker = DashboardWidgetsPicker("form_widgets_div")
    cancel_button = Button("Cancel")


class NewDashboardView(DashboardFormCommon):
    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.title.text == "Adding a new dashboard" and
            self.dashboards.is_opened and
            self.dashboards.tree.currently_selected == [
                "All Dashboards",
                "All Groups",
                self.context["object"].group
            ]
        )


class EditDashboardView(DashboardFormCommon):
    save_button = Button("Save")
    reset_button = Button("Reset")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.title.text == "Editing Dashboard {}".format(self.context["object"].name) and
            self.dashboards.is_opened and
            self.dashboards.tree.currently_selected == [
                "All Dashboards",
                "All Groups",
                self.context["object"].group,
                self.context["object"].name
            ]
        )


class EditDefaultDashboardView(EditDashboardView):

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.title.text == "Editing Dashboard {}".format(self.context["object"].name) and
            self.dashboards.is_opened and
            self.dashboards.tree.currently_selected == [
                "All Dashboards",
                "{} ({})".format(self.context["object"].title, self.context["object"].name)
            ]
        )


class DashboardDetailsView(CloudIntelReportsView):
    SAMPLE_DASHBOARD_ROOT = ".//div[@id='modules']"
    ITEM_TITLE_LOCATOR = ".//h3[contains(@class, 'panel-title')]"
    title = Text("#explorer_title_text")
    name = SummaryFormItem("Basic Information", "Name")
    tab_title = SummaryFormItem("Basic Information", "Tab Title")

    @property
    def selected_items(self):
        items = []
        for el in self.browser.elements(self.ITEM_TITLE_LOCATOR, self.SAMPLE_DASHBOARD_ROOT):
            items.append(self.browser.text(el))
        return items

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.title.text == 'Dashboard "{} ({})"'.format(
                self.context["object"].title,
                self.context["object"].name
            ) and
            self.dashboards.is_opened and
            self.dashboards.tree.currently_selected == [
                "All Dashboards",
                "All Groups",
                self.context["object"].group,
                self.context["object"].name
            ]
        )


class DefaultDashboardDetailsView(DashboardDetailsView):

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports and
            self.title.text == 'Dashboard "{} ({})"'.format(
                self.context["object"].title,
                self.context["object"].name
            ) and
            self.dashboards.is_opened and
            self.dashboards.tree.currently_selected == [
                "All Dashboards",
                "{} ({})".format(self.context["object"].title, self.context["object"].name)
            ]
        )


class Dashboard(Updateable, Pretty, Navigatable):
    pretty_attrs = ["name", "group", "title", "widgets"]

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
        """Create this Dashboard in the UI."""
        view = navigate_to(self, "Add")
        view.fill({
            "name": self.name,
            "tab_title": self.title,
            "locked": self.locked,
            "widget_picker": self.widgets
        })
        view.add_button.click()
        view = self.create_view(DashboardAllGroupsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_message('Dashboard "{}" was saved'.format(self.name))

    def update(self, updates):
        """Update this Dashboard in the UI.

        Args:
            updates: Provided by update() context manager.
        """
        view = navigate_to(self, "Edit")
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        for attr, value in updates.items():
            setattr(self, attr, value)
        view = self.create_view(DashboardDetailsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message('Dashboard "{}" was saved'.format(self.name))
        else:
            view.flash.assert_message(
                'Edit of Dashboard "{}" was cancelled by the user'.format(self.name))

    def delete(self, cancel=False):
        """Delete this Dashboard in the UI.

        Args:
            cancel: Whether to cancel the deletion (default False).
        """
        view = navigate_to(self, "Details")
        view.configuration.item_select(
            "Delete this Dashboard from the Database",
            handle_alert=not cancel
        )
        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            view = self.create_view(DashboardAllGroupsView)
            assert view.is_displayed
            view.flash.assert_no_error()


class DefaultDashboard(Updateable, Pretty, Navigatable):
    pretty_attrs = ["name", "title", "widgets"]

    def __init__(self, title="Default Dashboard", locked=None, widgets=None, appliance=None):
        Navigatable.__init__(self, appliance)
        self.title = title
        self.locked = locked
        self.widgets = widgets

    @property
    def name(self):
        """Name of Default Dashboard cannot be changed."""
        return "default"

    def update(self, updates):
        """Update Default Dashboard in the UI.

        Args:
            updates: Provided by update() context manager.
        """
        view = navigate_to(self, "Edit")
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        view = self.create_view(DefaultDashboardDetailsView)
        assert view.is_displayed
        if changed:
            view.flash.assert_success_message('Dashboard "{}" was saved'.format(self.name))
        else:
            view.flash.assert_success_message(
                'Edit of Dashboard "{}" was cancelled by the user'.format(self.name))


@navigator.register(Dashboard, "Add")
class DashboardNew(CFMENavigateStep):
    VIEW = NewDashboardView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.prerequisite_view.dashboards.tree.click_path(
            "All Dashboards",
            "All Groups",
            self.obj.group
        )
        self.prerequisite_view.configuration.item_select("Add a new Dashboard")


@navigator.register(Dashboard, "Edit")
class DashboardEdit(CFMENavigateStep):
    VIEW = EditDashboardView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.configuration.item_select("Edit this Dashboard")


@navigator.register(DefaultDashboard, "Edit")
class DefaultDashboardEdit(CFMENavigateStep):
    VIEW = EditDefaultDashboardView
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.prerequisite_view.configuration.item_select("Edit this Dashboard")


@navigator.register(Dashboard, "Details")
class DashboardDetails(CFMENavigateStep):
    VIEW = DashboardDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.prerequisite_view.dashboards.tree.click_path(
            "All Dashboards",
            "All Groups",
            self.obj.group,
            self.obj.name
        )


@navigator.register(DefaultDashboard, "Details")
class DefaultDashboardDetails(CFMENavigateStep):
    VIEW = DefaultDashboardDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.prerequisite_view.dashboards.tree.click_path(
            "All Dashboards",
            "{} ({})".format(self.obj.title, self.obj.name)
        )
