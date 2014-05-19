# -*- coding: utf-8 -*-
from cfme.fixtures import pytest_selenium as sel
from cfme.dashboard import Widget


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
