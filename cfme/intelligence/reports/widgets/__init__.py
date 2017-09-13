# -*- coding: utf-8 -*-
"""Page model for Cloud Intel / Reports / Dashboard Widgets"""
from cfme.utils.wait import wait_for
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from widgetastic.widget import Text, Checkbox
from widgetastic_manageiq import SummaryFormItem
from widgetastic_patternfly import Button, Input, BootstrapSelect
from navmazing import NavigateToAttribute
from cfme.intelligence.reports import CloudIntelReportsView


class BaseDashboardReportWidget(Updateable, Pretty, Navigatable):

    # This string is a title of a widget type in the tree
    TYPE = None
    # This string is a part of widgets title
    TITLE = None
    pretty_attrs = []

    def generate(self, wait=True, cancel=False, **kwargs):
        view = navigate_to(self, "Details")
        view.configuration.item_select(
            "Generate Widget content now",
            handle_alert=not cancel
        )
        view.flash.assert_message("Content generation for this Widget has been initiated")
        view.flash.assert_no_error()
        if wait:
            self.wait_generated(**kwargs)

    def refresh(self):
        view = navigate_to(self, "Details")
        view.reload_button.click()

    def wait_generated(self, timeout=600):
        wait_for(
            self.check_status,
            num_sec=timeout, delay=5, fail_condition=lambda result: result != "Complete",
            fail_func=self.refresh)

    def check_status(self):
        view = navigate_to(self, "Details")
        return view.status_info.text

    def create(self):
        """Create this Widget in the UI."""
        view = navigate_to(self, "Add")
        view.fill(self.fill_dict)
        view.add_button.click()
        view = self.create_view(AllDashboardWidgetsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        view.flash.assert_message('Widget "{}" was saved'.format(self.title))

    def update(self, updates):
        """Update this Widget in the UI.

        Args:
            updates: Provided by update() context manager.
            cancel: Whether to cancel the update (default False).
        """
        view = navigate_to(self, "Edit")
        changed = view.fill(updates)
        if changed:
            view.save_button.click()
        else:
            view.cancel_button.click()
        for attr, value in updates.items():
            setattr(self, attr, value)
        view = self.create_view(DashboardWidgetDetailsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message('Widget "{}" was saved'.format(self.title))
        else:
            view.flash.assert_message(
                'Edit of Widget "{}" was cancelled by the user'.format(self.description))

    def delete(self, cancel=False):
        """Delete this Widget in the UI.

        Args:
            cancel: Whether to cancel the deletion (default False).
        """
        view = navigate_to(self, "Details")
        view.configuration.item_select(
            "Delete this Widget from the Database",
            handle_alert=not cancel
        )
        if cancel:
            assert view.is_displayed
            view.flash.assert_no_error()
        else:
            view = self.create_view(AllDashboardWidgetsView)
            assert view.is_displayed
            view.flash.assert_no_error()


class DashboardWidgetsView(CloudIntelReportsView):

    @property
    def in_dashboard_widgets(self):
        return self.in_intel_reports and self.dashboard_widgets.is_opened

    @property
    def is_displayed(self):
        return self.in_dashboard_widgets


class AllDashboardWidgetsView(DashboardWidgetsView):
    title = Text("#explorer_title_text")

    @property
    def is_displayed(self):
        return (
            self.in_dashboard_widgets and
            self.title.text == "{} Widgets".format(self.context["object"].TITLE) and
            self.dashboard_widgets.tree.currently_selected == [
                "All Widgets",
                self.context["object"].TYPE
            ]
        )


class DashboardWidgetDetailsView(DashboardWidgetsView):

    title = Text("#explorer_title_text")
    status_info = SummaryFormItem("Status", "Current Status")
    reload_button = Button(title="Reload current display")

    @property
    def is_displayed(self):
        return (
            self.in_dashboard_widgets and
            self.title.text == '{} Widget "{}"'.format(
                self.context["object"].TITLE, self.context["object"].title) and
            self.dashboard_widgets.tree.currently_selected == [
                "All Widgets",
                self.context["object"].TYPE,
                self.context["object"].title
            ]
        )


class BaseDashboardWidgetFormCommon(DashboardWidgetsView):

    title = Text("#explorer_title_text")
    widget_title = Input(name="title")
    description = Input(name="description")
    active = Checkbox("enabled")
    visibility = BootstrapSelect("visibility_typ")
    # TODO add roles and groups CheckboxSelect
    cancel_button = Button("Cancel")


class BaseNewDashboardWidgetView(DashboardWidgetsView):

    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_dashboard_widgets and
            self.title.text == "Adding a new Widget" and
            self.dashboard_widgets.tree.currently_selected == [
                "All Widgets",
                self.context["object"].TYPE
            ]
        )


class BaseEditDashboardWidgetView(DashboardWidgetsView):

    save_button = Button("Save")
    reset_button = Button("Reset")

    @property
    def is_displayed(self):
        return (
            self.in_dashboard_widgets and
            self.title_text == 'Editing Widget "{}"'.format(self.context["object"]) and
            self.dashboard_widgets.tree.currently_selected == [
                "All Widgets",
                self.context["object"].TYPE,
                self.context["object"].title
            ]
        )


class BaseNewDashboardWidgetStep(CFMENavigateStep):
    VIEW = None
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.view.dashboard_widgets.tree.click_path(
            "All Widgets",
            self.obj.TYPE
        )
        self.view.configuration.item_select("Add a new Widget")


@navigator.register(BaseDashboardReportWidget, "Details")
class BaseDashboardWidgetDetailsStep(CFMENavigateStep):
    VIEW = DashboardWidgetDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.view.dashboard_widgets.tree.click_path(
            "All Widgets",
            self.obj.TYPE,
            self.obj.title
        )


class BaseEditDashboardWidgetStep(BaseDashboardWidgetDetailsStep):

    def step(self):
        super(BaseEditDashboardWidgetStep, self).step()
        self.view.configuration.item_select("Edit this Widget")
