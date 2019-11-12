import pytest

from cfme.dashboard import Widget
from cfme.intelligence.reports import widgets
from cfme.utils.appliance.implementations.ui import navigate_to


@pytest.fixture(scope="session")
def widgets_generated(setup_only_one_provider, appliance):
    navigate_to(appliance.server, 'Dashboard')
    widget_list = []
    for widget in Widget.all():
        widget_list.append((widget.name, widget.content_type))
    for w_name, w_type in widget_list:
        w = widgets.Widget.detect(w_type, w_name)
        if w.check_status() in w.WAIT_STATES:
            w.wait_generated(timeout=15 * 60)
        else:
            w.generate(timeout=15 * 60)
