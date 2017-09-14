# -*- coding: utf-8 -*-

import pytest
from cfme import test_requirements
from cfme.configure.settings import visual
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import ColorGroup, form_buttons
from cfme.utils.appliance import current_appliance
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils import version
from cfme.configure import settings  # NOQA


pytestmark = [pytest.mark.tier(3),
              test_requirements.settings]

colors = [
    'Orange',
    'Yellow',
    'Green',
    'Blue',
    'ManageIQ-Blue',
    'Black',
]


@pytest.yield_fixture(scope="module")
def set_timezone():
    time_zone = visual.timezone
    visual.timezone = "(GMT-10:00) Hawaii"
    yield
    visual.timezone = time_zone


def set_header_color(name):
    cg = ColorGroup('Header Accent Color')
    if cg.active != name:
        cg.choose(name)
        sel.click(form_buttons.save)


def is_header_color_changed(name):
    cg = ColorGroup('Header Accent Color')
    if cg.active == name:
        return cg.status(name)


def reset_default_color(default_color):
    cg = ColorGroup('Header Accent Color')
    if cg.active != default_color:
        cg.choose(default_color)
        sel.click(form_buttons.save)


def test_timezone_setting(set_timezone):
    """ Tests  timezone setting

    Metadata:
        test_flag: visuals
    """
    locator = version.pick({
        version.LOWEST: ('//label[contains(@class,"control-label") and contains(., "Started On")]'
            '/../div/p[contains(., "{}")]'.format("HST")),
        '5.7': ('//label[contains(@class,"control-label") and contains(., "Started On")]'
            '/../div/p[contains(., "{}")]'.format("-1000"))
    })

    navigate_to(current_appliance.server, 'DiagnosticsDetails')

    assert sel.is_displayed(locator), "Timezone settings Failed"
