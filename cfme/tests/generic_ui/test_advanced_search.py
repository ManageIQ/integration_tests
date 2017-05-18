# -*- coding: utf-8 -*-
"""

This testing module tests the generic behaviour of the advanced search box

This can/should be parameterized for all of the screens where advanced search is possible
There are existing advanced search tests that could be consolidated from infrastructure
    and moved here to cover containers, cloud, and infra as params.

"""
import pytest

import cfme.fixtures.pytest_selenium as sel
from cfme.infrastructure.provider import InfraProvider
from cfme.web_ui import search
from utils.appliance.implementations.ui import navigate_to
from utils.providers import setup_a_provider


pytestmark = [pytest.mark.tier(3)]

search_buttons = ['apply_filter_button', 'load_filter_button', 'save_filter_button',
                  'reset_filter_button']


@pytest.fixture(scope="module")
def provider():
    try:
        # paramaterize provider type
        setup_a_provider(prov_class="infra")
        navigate_to(InfraProvider, 'All')
    except Exception as ex:
        pytest.skip("Exception setting up provider: {}".format(ex.message))


def test_can_do_advanced_search(provider):
    navigate_to(provider, 'All')
    assert search.is_advanced_search_possible()


# @pytest.mark.meta(blockers=[1380430])
@pytest.mark.parametrize('button', search_buttons)
def test_advanced_search_button_alt(provider, button):
    # testing state of the buttons in the default advanced search box
    # need to clear any existing filters, including the filter expressions, to get to default state
    search.ensure_no_filter_applied(clear_expression=True)
    search.ensure_advanced_search_open()
    assert sel.is_displayed(getattr(search.search_box, button).locate)
