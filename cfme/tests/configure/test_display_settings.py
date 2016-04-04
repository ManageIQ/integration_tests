# -*- coding: utf-8 -*-

import pytest
from cfme.configure.settings import visual
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import ColorGroup, form_buttons
from utils.conf import cfme_data
from cfme.configure import settings  # NOQA

pytestmark = [pytest.mark.tier(3)]

try:
    displaysettings = cfme_data.displaysettings.color
except KeyError:
    displaysettings = []
grid_uncollectif = pytest.mark.uncollectif(not displaysettings, reason='no settings configured')


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
    locator = '//label[contains(@class,"control-label") and contains(., "Started On")]'\
              '/../div/p[contains(., "{}")]'.format("HST")

    sel.force_navigate("cfg_diagnostics_server_summary")
    assert sel.is_displayed(locator), "Timezone settings Failed"
