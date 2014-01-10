"""
cfme.dashboard
--------------

The :py:mod:`cfme.dashboard` module provides functions to the dashboard landing page.

:var page: A :py:class:`cfme.web_ui.Region` holding locators on the dashboard page
"""

from selenium.webdriver.common.by import By
import cfme.fixtures.pytest_selenium as browser
from cfme.web_ui import Region, handle_popup

_css_reset_button = 'div.dhx_toolbar_btn[title="Reset Dashboard Widgets to the defaults"] img'

page = Region(title="CloudForms Management Engine: Dashboard",
              locators={'reset_widgets_button': (By.CSS_SELECTOR, _css_reset_button)})


def reset_widgets(cancel=False):
    """
    Resets the widgets on the dashboard page.

    Args:
        cancel: Set whether to accept the popup confirmation box. Defaults to ``False``.
    """
    browser().click(page.reset_widgets_button)
    handle_popup(cancel)
