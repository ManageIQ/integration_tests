# -*- coding: utf-8 -*-

import pytest
from cfme.configure.settings import visual
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import ColorGroup, form_buttons
from utils.conf import cfme_data
from utils import version
from cfme.configure import settings  # NOQA

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
    locator = version.pick({
        version.LOWEST: '//div[@id="time"][contains(., "%s")]' % ("HST"),
        '5.4': '//div[@class="container-fluid"][contains(., "%s")]' % ("HST"),
        '5.5': '//label[contains(@class,"control-label") and contains(., "Started On")]'
               '/../div/p[contains(., "%s")]' % ("HST")
    })

    if version.current_version() > '5.5':
        sel.force_navigate("cfg_diagnostics_server_summary")
    else:
        sel.force_navigate("my_settings_visual")

    assert sel.is_displayed(locator), "Timezone settings Failed"


@grid_uncollectif
@pytest.mark.uncollectif(lambda: version.current_version() >= "5.4")
@pytest.mark.parametrize('name', displaysettings, scope="module")
def test_color_setting(request, name):
    """ Tests  color settings

    Metadata:
        test_flag: visuals
    """
    sel.force_navigate("my_settings_visual")
    cg = ColorGroup('Header Accent Color')
    default_color = cg.active
    set_header_color(name)
    assert is_header_color_changed(name), "Header Accent Color setting failed"
    reset_default_color(default_color)
