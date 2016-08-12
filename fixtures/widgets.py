# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import pytest

from cfme.dashboard import Widget
from cfme.intelligence.reports import widgets


@pytest.fixture(scope="session")
def widgets_generated(any_provider_session):
    pytest.sel.force_navigate("dashboard")
    widget_list = []
    for widget in Widget.all():
        widget_list.append((widget.name, widget.content_type))
    for w_name, w_type in widget_list:
        w = widgets.Widget.detect(w_type, w_name)
        if w.check_status() in w.WAIT_STATES:
            w.wait_generated(timeout=15 * 60)
        else:
            w.generate(timeout=15 * 60)
