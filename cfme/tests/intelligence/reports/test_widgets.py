# -*- coding: utf-8 -*-
""""""
import fauxfactory
import pytest

from cfme.fixtures import pytest_selenium as sel
from cfme.dashboard import Widget
from cfme.intelligence.reports.widgets import MenuWidget, ReportWidget, RSSFeedWidget, ChartWidget
from cfme.intelligence.reports.dashboards import DefaultDashboard
from utils.update import update


@pytest.fixture(scope="module")
def default_widgets():
    sel.force_navigate("reports_default_dashboard_edit")
    return DefaultDashboard.form.widgets.selected_items


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


@pytest.mark.tier(3)
def test_widgets_on_dashboard(request, dashboard, default_widgets, custom_widgets, soft_assert):
    with update(dashboard):
        dashboard.widgets = map(lambda w: w.title, custom_widgets)

    def _finalize():
        with update(dashboard):
            dashboard.widgets = default_widgets
    request.addfinalizer(_finalize)
    dashboard.reset_widgets()
    soft_assert(len(Widget.all()) == len(custom_widgets), "Count of the widgets differ")
    for custom_w in custom_widgets:
        try:
            Widget.by_name(custom_w.title)
        except NameError:
            soft_assert(False, "Widget {} not found on dashboard".format(custom_w.title))
