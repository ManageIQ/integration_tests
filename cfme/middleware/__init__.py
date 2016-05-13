from functools import partial

from cfme.common import Validatable
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb
from utils.browser import ensure_browser_open

cfg_btn = partial(tb.select, 'Configuration')
mon_btn = partial(tb.select, 'Monitoring')
pol_btn = partial(tb.select, 'Policy')
pwr_btn = partial(tb.select, 'Power')

LIST_TABLE_LOCATOR = "//div[@id='list_grid']/table"


class MiddlewareBase(Validatable):
    """
    MiddlewareBase class used to define common functions across pages.
    Also used to override existing function when required.
    """

    def _on_detail_page(self):
        """ Returns ``True`` if on the providers detail page, ``False`` if not."""
        ensure_browser_open()
        return sel.is_displayed('//h1[contains(., "{} (Summary)")]'.format(self.name))
