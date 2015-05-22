# -*- coding: utf-8 -*-
import pytest

from cfme.dashboard import Widget
from cfme.intelligence.reports import widgets

from utils.wait import wait_for

WAIT_STATES = {"Queued", "Running"}


@pytest.fixture(scope="session")
def widgets_generated(any_provider_session):
    pytest.sel.force_navigate("dashboard")
    widget_list = []
    for widget in Widget.all():
        widget_list.append((widget.name, widget.content_type))
    for w_name, w_type in widget_list:
        w = widgets.Widget.detect(w_type, w_name)
        wait_for(w.check_status, fail_condition=WAIT_STATES, delay=5, num_sec=180)
        w.generate()
