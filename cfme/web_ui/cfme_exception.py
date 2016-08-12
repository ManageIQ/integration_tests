# -*- coding: utf-8 -*-
"""Module handling the Rails exceptions from CFME"""

from __future__ import unicode_literals
from cfme.exceptions import CFMEExceptionOccured
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Region


cfme_exception_region = Region(
    locators=dict(
        root_div="//div[@id='exception_div']",
        error_text="//div[@id='exception_div']//td[@id='maincol']/div[2]/h3[2]",
    ),
    identifying_loc="root_div",
)


def is_cfme_exception():
    """Check whether an exception is displayed on the page"""
    return cfme_exception_region.is_displayed()


def cfme_exception_text():
    """Get the error message from the exception"""
    return sel.text(cfme_exception_region.error_text)


def assert_no_cfme_exception():
    """Raise an exception if CFME exception occured

    Raises: :py:class:`cfme.exceptions.CFMEExceptionOccured`
    """
    if is_cfme_exception():
        raise CFMEExceptionOccured(cfme_exception_text())
