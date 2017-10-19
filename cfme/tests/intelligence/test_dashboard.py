# -*- coding: utf-8 -*-
import re

import fauxfactory
import pytest
import requests
from random import sample

from cfme import test_requirements
from cfme.intelligence.reports.dashboards import Dashboard
from cfme.utils.blockers import BZ
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


@pytest.yield_fixture(scope='function')
def widgets(dashboards):
    yield dashboards.default.collections.widgets.all()
    dashboards.close_zoom()
    dashboards.default.collections.widgets.reset()


@pytest.mark.meta(blockers=[1476305])
def test_widgets_operation(dashboards, widgets, soft_assert, infra_provider):
    # We need to make sure the widgets have some data.
    wait_for(
        lambda: all(not widget.blank for widget in widgets),
        timeout='5m', delay=10,
        fail_func=lambda: dashboards.refresh())
    # Then we can check the operations
    for widget in widgets:
        widget.minimize()
        soft_assert(widget.minimized, 'Widget {} could not be minimized'.format(widget.name))
        widget.restore()
        soft_assert(not widget.minimized, 'Widget {} could not be maximized'.format(widget.name))
        # TODO: Once modal problems resolved, uncomment
        # if widget.can_zoom:
        #     widget.zoom()
        #     assert widget.is_zoomed
        #     widget.close_zoom()
        #     assert not widget.is_zoomed
        widget.footer
        widget.contents
        if widget.content_type in ['chart', 'table']:
            widget.widget_view.menu.select("Download PDF")
        assert widget.dashboard.dashboard_view.is_displayed


@pytest.mark.parametrize("number_dashboards", range(1, 4))
def test_custom_dashboards(request, soft_assert, number_dashboards, dashboards):
    """Create some custom dashboards and check their presence. Then check their contents."""
    # Very useful construct. List is mutable, so we can prepare the generic delete finalizer.
    # Then we add everything that succeeded with creation. Simple as that :)
    dashboards_to_delete = []
    request.addfinalizer(lambda: map(lambda item: item.delete(), dashboards_to_delete))

    def _create_dashboard(widgets):
        return Dashboard(
            fauxfactory.gen_alphanumeric(),
            "EvmGroup-super_administrator",
            fauxfactory.gen_alphanumeric(),
            locked=False,
            widgets=widgets
        )

    for i in range(number_dashboards):
        d = _create_dashboard(sample(AVAILABLE_WIDGETS, 3))
        d.create()
        dashboards_to_delete.append(d)
    dash_dict = {d.title: d for d in dashboards_to_delete}
    try:
        for dash in dashboards.all():
            soft_assert(dash.name in dash_dict, "Dashboard {} not found!".format(dash.name))
            if dash.name in dash_dict:
                for widget in dash.widgets.all():
                    soft_assert(widget.name in dash_dict[dash.name].widgets,
                                "Widget {} not found in {}!".format(widget.name, dash.name))
                del dash_dict[dash.name]
        soft_assert(not dash_dict, "Some of the dashboards were not found! ({})".format(
            ", ".join(dash_dict.keys())))
    except IndexError:
        pytest.fail("No dashboard selection tabs present on dashboard!")


def test_verify_rss_links(dashboards):
    """This test verifies that RSS links on dashboard are working.

    Prerequisities:
        * Generated widgets, at least one RSS.

    Steps:
        * Loop through all RSS widgets
        * Loop through all the links in a widget
        * Try making a request on the provided URLs, should make sense
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


@pytest.mark.meta(blockers=[BZ(1316134, forced_streams=['5.7', '5.8', 'upstream'])])
def test_drag_and_drop_widget_to_the_bottom_of_another_column(dashboards, request):
    """In this test we try to drag and drop a left upper widget to
       the bottom of the middle column.

       Prerequisities:
        * A list of widgets on the default dashboard

       Steps:
        * Go to the Dashboard
        * Drag a left upper widget and drop it under the bottom widget of the near column
        * Assert that the widgets order is changed
    """
    request.addfinalizer(dashboards.default.collections.widgets.reset)
    first_column = dashboards.default.dashboard_view.column_widget_names(1)
    second_column = dashboards.default.dashboard_view.column_widget_names(2)

    first_widget_name = first_column[0]
    second_widget_name = second_column[-1]
    dashboards.default.drag_and_drop(first_widget_name, second_widget_name)

    assert dashboards.default.dashboard_view.column_widget_names(2)[-1] == first_widget_name
