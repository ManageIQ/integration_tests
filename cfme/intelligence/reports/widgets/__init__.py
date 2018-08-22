import attr
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text, Checkbox
from widgetastic_manageiq import SummaryFormItem
from widgetastic_patternfly import Button, Input, BootstrapSelect

from cfme.intelligence.reports import CloudIntelReportsView
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.wait import wait_for
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to


@attr.s
class BaseDashboardReportWidget(BaseEntity, Updateable, Pretty):

    # This string is a title of a widget type in the tree
    TYPE = None
    # This string is a part of widgets title
    TITLE = None
    pretty_attrs = []
    title = attr.ib()
    description = attr.ib()
    active = attr.ib()
    visibility = attr.ib(default=None)

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

    def update(self, updates):
        """Update this Widget in the UI.

        Args:
            updates: Provided by update() context manager.
        """
        # In order to update the tree in the side menu we have to refresh a whole page
        self.browser.refresh()
        view = navigate_to(self, "Edit")
        changed = view.fill_with(
            updates,
            on_change=view.save_button.click,
            no_change=view.cancel_button.click
        )
        view = self.create_view(DashboardWidgetDetailsView, override=updates)
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
        if not cancel:
            view = self.create_view(AllDashboardWidgetsView)
        assert view.is_displayed
        view.flash.assert_no_error()


@attr.s
class DashboardReportWidgetsCollection(BaseCollection):
    ENTITY = BaseDashboardReportWidget

    @property
    def CHART(self):  # noqa
        from cfme.intelligence.reports.widgets.chart_widgets import ChartWidget
        return ChartWidget

    @property
    def MENU(self):  # noqa
        from cfme.intelligence.reports.widgets.menu_widgets import MenuWidget
        return MenuWidget

    @property
    def RSS(self):  # noqa
        from cfme.intelligence.reports.widgets.rss_widgets import RSSFeedWidget
        return RSSFeedWidget

    @property
    def REPORT(self):  # noqa
        from cfme.intelligence.reports.widgets.report_widgets import ReportWidget
        return ReportWidget

    def instantiate(self, widget_class, *args, **kwargs):
        return widget_class.from_collection(self, *args, **kwargs)

    def create(self, widget_class, *args, **kwargs):
        """Create this Widget in the UI."""
        dashboard_widget = self.instantiate(widget_class, *args, **kwargs)
        view = navigate_to(dashboard_widget, "Add")
        view.fill_with(dashboard_widget.fill_dict, on_change=view.add_button.click)
        view = dashboard_widget.create_view(AllDashboardWidgetsView)
        assert view.is_displayed
        view.flash.assert_no_error()
        return dashboard_widget


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
    reload_button = Button(title='Refresh this page')

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
        self.view.dashboard_widgets.tree.click_path("All Widgets", self.obj.TYPE)
        self.view.configuration.item_select("Add a new Widget")


@navigator.register(BaseDashboardReportWidget, "Details")
class BaseDashboardWidgetDetailsStep(CFMENavigateStep):
    VIEW = DashboardWidgetDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self):
        self.view.dashboard_widgets.tree.click_path("All Widgets", self.obj.TYPE, self.obj.title)


class BaseEditDashboardWidgetStep(BaseDashboardWidgetDetailsStep):
    VIEW = None
    prerequisite = NavigateToSibling("Details")

    def step(self):
        self.view.configuration.item_select("Edit this Widget")
