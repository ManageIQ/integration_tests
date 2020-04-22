import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import Checkbox
from widgetastic.widget import FileInput
from widgetastic.widget import Select
from widgetastic.widget import Text
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Input

from cfme.intelligence.reports import CloudIntelReportsView
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.blockers import BZ
from cfme.utils.pretty import Pretty
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for
from widgetastic_manageiq import InputButton
from widgetastic_manageiq import SummaryFormItem
from widgetastic_manageiq import Table


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
        view = navigate_to(self, "Edit", use_resetter=False)
        changed = view.fill_with(
            updates,
            on_change=view.save_button.click,
            no_change=view.cancel_button.click
        )
        view = self.create_view(DashboardWidgetDetailsView, override=updates, wait='10s')
        view.flash.assert_no_error()
        if changed:
            view.flash.assert_message(f'Widget "{self.title}" was saved')
        else:
            view.flash.assert_message(
                f'Edit of Widget "{self.description}" was cancelled by the user')

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
        view = dashboard_widget.create_view(AllDashboardWidgetsView, wait='10s')
        view.flash.assert_no_error()
        return dashboard_widget

    def import_widget(self, filepath, cancel=False):
        """
        Import yaml files containing widget data
        Args:
            filepath (str): Complete path to the file
            cancel (bool): If true, widgets will not be imported
        """
        view = navigate_to(self, "ImportExport")

        view.fill({"upload_file": filepath})
        view.upload_button.click()
        view.flash.assert_no_error()

        import_view = self.create_view(ImportExportWidgetsCommitView, wait='5s')
        import_view.table.check_all()

        if cancel:
            import_view.cancel_button.click()
            view.flash.assert_message("Widget import cancelled")
        else:
            import_view.commit_button.click()
            import_view.flash.assert_no_error()

    def export_widget(self, *widgets):
        """
        Export custom widgets
        Args:
            widgets (str, tuple): name of widgets to be exported
        """
        view = navigate_to(self, "ImportExport")

        view.items_for_export.fill(*widgets)
        view.export_button.click()
        view.flash.assert_no_error()


class DashboardWidgetsView(CloudIntelReportsView):

    @property
    def in_dashboard_widgets(self):
        return self.in_intel_reports and self.dashboard_widgets.is_opened

    @property
    def is_displayed(self):
        return self.in_dashboard_widgets

    def correct_tree_menu_item_selected(self):
        # This workaround is needed for the test_menuwidget_crud and perhaps
        # some other tests.
        if BZ(1667064, forced_streams=['5.11']).blocks:
            return True

        return self.dashboard_widgets.tree.currently_selected == [
            "All Widgets",
            self.context["object"].TYPE,
            self.context["object"].title
        ]


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
    last_run_time = SummaryFormItem("Status", "Last Run Time")
    reload_button = Button(title='Refresh this page')

    @property
    def is_displayed(self):
        return (
            self.in_dashboard_widgets and
            self.title.text == '{} Widget "{}"'.format(
                self.context["object"].TITLE, self.context["object"].title) and
            self.correct_tree_menu_item_selected()
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
            self.title.text == 'Editing Widget "{}"'.format(self.context["object"].title) and
            self.correct_tree_menu_item_selected()
        )


class ImportExportWidgetsView(CloudIntelReportsView):
    title = Text("#explorer_title_text")
    subtitle = Text(locator=".//div[@id='main_div']/h2")

    upload_file = FileInput(id="upload_file")
    upload_button = InputButton("commit")

    items_for_export = Select(id="widgets_")
    export_button = Button(value="Export")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports
            and self.title.text == "Import / Export"
            and self.subtitle.text == "Widgets"
            and self.import_export.tree.currently_selected
            == ["Import / Export", "Widgets"]
        )


class ImportExportWidgetsCommitView(CloudIntelReportsView):

    title = Text("#explorer_title_text")
    table = Table(".//form[@id='import-widgets-form']/table")
    commit_button = Button(value="Commit")
    cancel_button = Button(value="Cancel")

    @property
    def is_displayed(self):
        return (
            self.in_intel_reports
            and self.title.text == "Import / Export"
            and self.import_export.tree.currently_selected
            == ["Import / Export", "Widgets"]
        )


class BaseNewDashboardWidgetStep(CFMENavigateStep):
    VIEW = None
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self, *args, **kwargs):
        self.view.dashboard_widgets.tree.click_path("All Widgets", self.obj.TYPE)
        self.view.configuration.item_select("Add a new Widget")


@navigator.register(BaseDashboardReportWidget, "Details")
class BaseDashboardWidgetDetailsStep(CFMENavigateStep):
    VIEW = DashboardWidgetDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self, *args, **kwargs):
        self.view.dashboard_widgets.tree.click_path("All Widgets", self.obj.TYPE, self.obj.title)


class BaseEditDashboardWidgetStep(BaseDashboardWidgetDetailsStep):
    VIEW = None
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.view.configuration.item_select("Edit this Widget")


@navigator.register(DashboardReportWidgetsCollection, "ImportExport")
class ImportExportWidgets(CFMENavigateStep):
    VIEW = ImportExportWidgetsView
    prerequisite = NavigateToAttribute("appliance.server", "CloudIntelReports")

    def step(self, *args, **kwargs):
        self.prerequisite_view.import_export.tree.click_path("Import / Export", "Widgets")
