# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.base import Server
from cfme.dashboard import Widget
from cfme.intelligence.reports.widgets.menu_widgets import MenuWidget
from cfme.intelligence.reports.widgets.report_widgets import ReportWidget
from cfme.intelligence.reports.widgets.chart_widgets import ChartWidget
from cfme.intelligence.reports.widgets.rss_widgets import RSSFeedWidget
from cfme.intelligence.reports.dashboards import DefaultDashboard
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update
from cfme import test_requirements


@pytest.fixture(scope="module")
def default_widgets():
    view = navigate_to(DefaultDashboard(), 'Details')
    return view.selected_items


@pytest.fixture(scope="module")
def dashboard(default_widgets):
    return DefaultDashboard(widgets=default_widgets)


@pytest.fixture(scope="function")
def custom_widgets(request):
    ws = [
        MenuWidget(
            fauxfactory.gen_alphanumeric(),
            description=fauxfactory.gen_alphanumeric(),
            active=True,
            shortcuts={
                "Services / Catalogs": fauxfactory.gen_alphanumeric(),
                "Clouds / Providers": fauxfactory.gen_alphanumeric(),
            },
            visibility="<To All Users>"),
        ReportWidget(
            fauxfactory.gen_alphanumeric(),
            description=fauxfactory.gen_alphanumeric(),
            active=True,
            filter=["Events", "Operations", "Operations VMs Powered On/Off for Last Week"],
            columns=["VM Name", "Message"],
            rows="10",
            timer={"run": "Hourly", "hours": "Hour"},
            visibility="<To All Users>"),
        ChartWidget(
            fauxfactory.gen_alphanumeric(),
            description=fauxfactory.gen_alphanumeric(),
            active=True,
            filter="Configuration Management/Virtual Machines/Vendor and Guest OS",
            timer={"run": "Hourly", "hours": "Hour"},
            visibility="<To All Users>"),
        RSSFeedWidget(
            fauxfactory.gen_alphanumeric(),
            description=fauxfactory.gen_alphanumeric(),
            active=True,
            type="Internal",
            feed="Administrative Events",
            rows="8",
            visibility="<To All Users>"),
    ]
    map(lambda w: w.create(), ws)  # create all widgets
    request.addfinalizer(lambda: map(lambda w: w.delete(), ws))  # Delete them after test
    return ws


@test_requirements.dashboard
@pytest.mark.tier(3)
def test_widgets_on_dashboard(request, dashboard, default_widgets, custom_widgets, soft_assert):
    with update(dashboard):
        dashboard.widgets = map(lambda w: w.title, custom_widgets)

    def _finalize():
        with update(dashboard):
            dashboard.widgets = default_widgets
    request.addfinalizer(_finalize)
    view = navigate_to(Server, "Dashboard")
    view.reset_widgets()
    soft_assert(len(Widget.all()) == len(custom_widgets), "Count of the widgets differ")
    for custom_w in custom_widgets:
        try:
            Widget.by_name(custom_w.title)
        except NameError:
            soft_assert(False, "Widget {} not found on dashboard".format(custom_w.title))


@test_requirements.dashboard
@pytest.mark.tier(3)
def test_widgets_reorder_in_reports(request, dashboard):
    """Tests drag and drop widgets in Cloud Intel/Reports/Dashboards"""
    view = navigate_to(dashboard, "Edit")
    previous_names = view.widget_picker.all_dashboard_widgets
    first_widget = previous_names[0]
    second_widget = previous_names[1]
    view.widget_picker.drag_and_drop(first_widget, second_widget)
    new_names = view.widget_picker.all_dashboard_widgets
    assert previous_names[2:] == new_names[2:]
    assert previous_names[0] == new_names[1]
    assert previous_names[1] == new_names[0]
