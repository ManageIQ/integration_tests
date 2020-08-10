import re
from random import sample

import fauxfactory
import pytest
import requests

from cfme import test_requirements
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.dashboard,
    pytest.mark.tier(3)
]

AVAILABLE_WIDGETS = [
    "Top Memory Consumers (weekly)",
    "Vendor and Guest OS Chart",
    "EVM: Recently Discovered Hosts",
    "Top Storage Consumers",
    "Guest OS Information"
]


@pytest.fixture(scope='function')
def widgets(dashboards):
    yield dashboards.default.collections.widgets.all()
    dashboards.close_zoom()
    dashboards.default.collections.widgets.reset()


def test_widgets_operation(dashboards, widgets, soft_assert, infra_provider):
    """
    Polarion:
        assignee: jhenner
        caseimportance: critical
        casecomponent: Reporting
        initialEstimate: 1/12h
    """
    # We need to make sure the widgets have some data.
    wait_for(
        lambda: all(not widget.blank for widget in widgets),
        timeout='5m', delay=10,
        fail_func=lambda: dashboards.refresh())
    # Then we can check the operations
    for widget in widgets:
        widget.minimize()
        soft_assert(widget.minimized, f'Widget {widget.name} could not be minimized')
        widget.restore()
        soft_assert(not widget.minimized, f'Widget {widget.name} could not be maximized')

        if widget.can_zoom:
            widget.zoom()
            assert widget.is_zoomed
            widget.close_zoom()
            assert not widget.is_zoomed
        widget.footer
        widget.contents
        if widget.content_type in ['chart', 'table']:
            # widget.widget_view.menu.select("Print or export to PDF")
            #
            # We may never reach this as the tests are been blocked by it when
            # using Chromium.
            pass

        assert widget.dashboard.dashboard_view.is_displayed


@pytest.mark.rhel_testing
@pytest.mark.parametrize("number_dashboards", list(range(1, 4)))
def test_custom_dashboards(request, soft_assert, number_dashboards, dashboards, appliance):
    """Create some custom dashboards and check their presence. Then check their contents.

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Reporting
        initialEstimate: 1/12h

    Bugzilla:
        1666712
    """
    # Very useful construct. List is mutable, so we can prepare the generic delete finalizer.
    # Then we add everything that succeeded with creation. Simple as that :)
    dashboards_to_delete = []
    request.addfinalizer(lambda: [item.delete() for item in dashboards_to_delete])
    for _ in range(number_dashboards):
        d = appliance.collections.report_dashboards.create(
            fauxfactory.gen_alphanumeric(),
            "EvmGroup-super_administrator",
            fauxfactory.gen_alphanumeric(),
            locked=False,
            widgets=sample(AVAILABLE_WIDGETS, 3)
        )
        dashboards_to_delete.append(d)
    dash_dict = {d.title: d for d in dashboards_to_delete}
    try:
        for dash in dashboards.all():
            soft_assert(dash.name in dash_dict, f"Dashboard {dash.name} not found!")
            dash.dashboard_view.click()
            if dash.name in list(dash_dict.keys()):
                for widget in dash.collections.widgets.all():
                    soft_assert(widget.name in dash_dict[dash.name].widgets,
                                f"Widget {widget.name} not found in {dash.name}!")
                del dash_dict[dash.name]
        soft_assert(not dash_dict, "Some of the dashboards were not found! ({})".format(
            ", ".join(list(dash_dict.keys()))))
    except IndexError:
        pytest.fail("No dashboard selection tabs present on dashboard!")


def test_verify_rss_links_from_dashboards(dashboards):
    """This test verifies that RSS links on dashboard are working.

    Prerequisities:
        * Generated widgets, at least one RSS.

    Steps:
        * Loop through all RSS widgets
        * Loop through all the links in a widget
        * Try making a request on the provided URLs, should make sense

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: WebUI
        initialEstimate: 1/4h
    """
    wait_for(
        lambda: not any(widget.blank for widget in dashboards.default.collections.widgets.all()),
        delay=2,
        timeout=120,
        fail_func=dashboards.refresh)
    for widget in dashboards.default.collections.widgets.all(content_type="rss"):
        for row in widget.contents:
            onclick = row.browser.get_attribute('onclick', row)
            url = re.sub(r'^window.location="([^"]+)";$', '\\1', onclick.strip())
            req = requests.get(url, verify=False)
            assert 200 <= req.status_code < 400, "The url {} seems malformed".format(repr(url))


def test_widgets_reorder(dashboards, soft_assert, request):
    """In this test we try to reorder first two widgets in the first column of a
       default dashboard.

       Prerequisities:
        * A list of widgets on the default dashboard

       Steps:
        * Go to the Dashboard
        * Reorder first two widgets in the first column using drag&drop
        * Assert that the widgets order is changed

    Polarion:
        assignee: jhenner
        caseimportance: high
        casecomponent: Reporting
        initialEstimate: 1/12h
    """
    request.addfinalizer(dashboards.default.collections.widgets.reset)
    previous_state = dashboards.default.collections.widgets.all()
    previous_names = [w.name for w in previous_state]
    first_widget = previous_state[0]
    second_widget = previous_state[1]
    dashboards.default.drag_and_drop(first_widget, second_widget)
    new_state = dashboards.default.collections.widgets.all()
    new_names = [w.name for w in new_state]
    assert previous_names[2:] == new_names[2:]
    assert previous_names[0] == new_names[1]
    assert previous_names[1] == new_names[0]


@pytest.mark.manual
@test_requirements.dashboard
@pytest.mark.tier(3)
def test_dashboard_layouts_match():
    """
    Bugzilla:
        1518766

    Polarion:
        assignee: jhenner
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.dashboard
@pytest.mark.tier(3)
def test_dashboard_widgets_fullscreen():
    """
    Bugzilla:
        1518901

    Polarion:
        assignee: jhenner
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/12h
    """
    pass


@pytest.mark.manual
@test_requirements.dashboard
@pytest.mark.tier(3)
def test_dashboard_chart_widgets_size_in_modal():
    """
    Test whether dashboard chart widgets have correct size in modal
    window.

    Polarion:
        assignee: jhenner
        casecomponent: Reporting
        caseimportance: low
        initialEstimate: 1/6h
        testtype: nonfunctional
    """
    pass
