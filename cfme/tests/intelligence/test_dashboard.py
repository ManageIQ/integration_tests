# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import requests
from collections import namedtuple
from random import sample

from cfme import dashboard
from cfme.fixtures import pytest_selenium as sel
from cfme.dashboard import Widget
from cfme.intelligence.reports.dashboards import Dashboard, DefaultDashboard
from utils.blockers import BZ


AVAILABLE_WIDGETS = [
    "Top Memory Consumers (weekly)",
    "Vendor and Guest OS Chart",
    "EVM: Recently Discovered Hosts",
    "Top Storage Consumers",
    "Guest OS Information"
]


@pytest.yield_fixture
def widgets():
    all_widgets = Widget.all()
    Widgets = namedtuple('Widgets', ('all_widgets', 'all_widgets_ids'))
    yield Widgets(
        all_widgets=all_widgets,
        all_widgets_ids=[widget._div_id for widget in all_widgets]
    )
    DefaultDashboard.reset_widgets()


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1202394])
def test_widgets_operation(request):
    sel.force_navigate("dashboard")
    request.addfinalizer(lambda: Widget.close_zoom())
    for widget in Widget.all():
        widget.minimize()
        assert widget.is_minimized
        widget.restore()
        assert not widget.is_minimized
        if widget.can_zoom:
            widget.zoom()
            assert Widget.is_zoomed()
            assert widget.name == Widget.get_zoomed_name()
            Widget.close_zoom()
            assert not Widget.is_zoomed()
        widget.footer
        widget.content


@pytest.mark.tier(3)
@pytest.mark.meta(
    blockers=[
        BZ(1110171, unblock=lambda number_dashboards: number_dashboards != 1)
    ]
)
@pytest.mark.parametrize("number_dashboards", range(1, 4))
def test_custom_dashboards(request, soft_assert, number_dashboards):
    """Create some custom dashboards and check their presence. Then check their contents."""
    # Very useful construct. List is mutable, so we can prepare the generic delete finalizer.
    # Then we add everything that succeeded with creation. Simple as that :)
    dashboards = []
    request.addfinalizer(lambda: map(lambda item: item.delete(), dashboards))

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
        dashboards.append(d)
    dash_dict = {d.title: d for d in dashboards}
    try:
        for dash_name in dashboard.dashboards():
            soft_assert(dash_name in dash_dict, "Dashboard {} not found!".format(dash_name))
            if dash_name in dash_dict:
                for widget in Widget.all():
                    soft_assert(widget.name in dash_dict[dash_name].widgets,
                                "Widget {} not found in {}!".format(widget.name, dash_name))
                del dash_dict[dash_name]
        soft_assert(not dash_dict, "Some of the dashboards were not found! ({})".format(
            ", ".join(dash_dict.keys())))
    except IndexError:
        pytest.fail("No dashboard selection tabs present on dashboard!")


@pytest.mark.tier(3)
def test_verify_rss_links(widgets_generated):
    """This test verifies that RSS links on dashboard are working.

    Prerequisities:
        * Generated widgets, at least one RSS.

    Steps:
        * Loop through all RSS widgets
        * Loop through all the links in a widget
        * Try making a request on the provided URLs, should make sense
    """
    pytest.sel.force_navigate("dashboard")
    for widget in Widget.by_type("rss_widget"):
        for desc, date, url in widget.content.data:
            assert url is not None, "Widget {}, line {} - no URL!".format(
                repr(widget.name), repr(desc))
            req = requests.get(url, verify=False)
            assert 200 <= req.status_code < 400, "The url {} seems malformed".format(repr(url))


@pytest.mark.tier(3)
def test_widgets_reorder(widgets, soft_assert):
    """In this test we try to reorder first two widgets in the first column of a
       default dashboard.

       Prerequisities:
        * A list of widgets on the default dashboard

       Steps:
        * Go to the Dashboard
        * Reorder first two widgets in the first column using drag&drop
        * Assert that the widgets order is changed
    """
    first_widget = widgets.all_widgets[0]
    second_widget = widgets.all_widgets[1]
    old_widgets_ids_list = widgets.all_widgets_ids
    first_widget.drag_and_drop(second_widget)
    new_widgets_ids_list = [widget._div_id for widget in Widget.all()]
    (old_widgets_ids_list[0],
     old_widgets_ids_list[1]) = old_widgets_ids_list[1], old_widgets_ids_list[0]
    soft_assert(old_widgets_ids_list == new_widgets_ids_list, "Drag and drop failed.")


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[BZ(1316134, forced_streams=['5.4'])])
def test_drag_and_drop_widget_to_the_bottom_of_another_column(widgets, soft_assert):
    """In this test we try to drag and drop a left upper widget to
       the bottom of the middle column.

       Prerequisities:
        * A list of widgets on the default dashboard

       Steps:
        * Go to the Dashboard
        * Drag a left upper widget and drop it under the bottom widget of the near column
        * Assert that the widgets order is changed
    """
    first_widget = widgets.all_widgets[0]
    second_widget = widgets.all_widgets[1]
    old_widgets_ids_list = widgets.all_widgets_ids
    first_widget.drag_and_drop(second_widget)
    new_widgets_ids_list = [widget._div_id for widget in Widget.all()]
    popped_widget_id = old_widgets_ids_list.pop(0)
    # an index of widget below of which we want to put the left upper widget is 4
    old_widgets_ids_list.insert(4, popped_widget_id)
    soft_assert(old_widgets_ids_list == new_widgets_ids_list, "Drag and drop failed.")
