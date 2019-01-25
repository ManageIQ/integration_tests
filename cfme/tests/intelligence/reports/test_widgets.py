# -*- coding: utf-8 -*-
import fauxfactory
import pytest

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
def custom_widgets(appliance):
    collection = appliance.collections.dashboard_report_widgets
    ws = [
        collection.create(
            collection.MENU,
            fauxfactory.gen_alphanumeric(),
            description=fauxfactory.gen_alphanumeric(),
            active=True,
            shortcuts={
                "Services / Catalogs": fauxfactory.gen_alphanumeric(),
                "Compute / Clouds / Providers": fauxfactory.gen_alphanumeric(),
            },
            visibility="<To All Users>"),
        collection.create(
            collection.REPORT,
            fauxfactory.gen_alphanumeric(),
            description=fauxfactory.gen_alphanumeric(),
            active=True,
            filter=["Events", "Operations", "Operations VMs Powered On/Off for Last Week"],
            columns=["VM Name", "Message"],
            rows="10",
            timer={"run": "Hourly", "hours": "Hour"},
            visibility="<To All Users>"),
        collection.create(
            collection.CHART,
            fauxfactory.gen_alphanumeric(),
            description=fauxfactory.gen_alphanumeric(),
            active=True,
            filter="Configuration Management/Virtual Machines/Vendor and Guest OS",
            timer={"run": "Hourly", "hours": "Hour"},
            visibility="<To All Users>"),
        collection.create(
            collection.RSS,
            fauxfactory.gen_alphanumeric(),
            description=fauxfactory.gen_alphanumeric(),
            active=True,
            type="Internal",
            feed="Administrative Events",
            rows="8",
            visibility="<To All Users>")
    ]
    yield ws
    map(lambda w: w.delete(), ws)


@test_requirements.dashboard
@pytest.mark.tier(3)
def test_widgets_on_dashboard(appliance, request, dashboard, default_widgets,
                              custom_widgets, soft_assert):
    """
    Polarion:
        assignee: jhenner
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/12h
    """
    with update(dashboard):
        dashboard.widgets = map(lambda w: w.title, custom_widgets)

    def _finalize():
        with update(dashboard):
            dashboard.widgets = default_widgets
    request.addfinalizer(_finalize)
    view = navigate_to(appliance.server, "Dashboard")
    view.reset_widgets()
    dashboard_view = view.dashboards("Default Dashboard")
    soft_assert(len(dashboard_view.widgets.read()) == len(custom_widgets),
                "Count of the widgets differ")
    for custom_w in custom_widgets:
        soft_assert(dashboard_view.widgets(custom_w.title).is_displayed,
                    "Widget {} not found on dashboard".format(custom_w.title))


@test_requirements.dashboard
@pytest.mark.tier(3)
def test_widgets_reorder_in_reports(request, dashboard):
    """Tests drag and drop widgets in Cloud Intel/Reports/Dashboards

    Polarion:
        assignee: jhenner
        casecomponent: Reporting
        caseimportance: medium
        initialEstimate: 1/6h
    """
    view = navigate_to(dashboard, "Edit")
    previous_names = view.widget_picker.all_dashboard_widgets
    first_widget = previous_names[0]
    second_widget = previous_names[1]
    view.widget_picker.drag_and_drop(first_widget, second_widget)
    new_names = view.widget_picker.all_dashboard_widgets
    assert previous_names[2:] == new_names[2:]
    assert previous_names[0] == new_names[1]
    assert previous_names[1] == new_names[0]
