# -*- coding: utf-8 -*-

from cfme.fixtures import pytest_selenium as sel
from cfme.configure import about
import pytest
import requests


@pytest.mark.sauce
def test_about_links():
    sel.force_navigate('about')
    for link_key, link_loc in about.product_assistance.locators.items():
        href = sel.get_attribute(link_loc, 'href')
        try:
            resp = requests.head(href, verify=False, timeout=20)
        except (requests.Timeout, requests.ConnectionError) as ex:
            pytest.fail(ex.message)

        assert 200 <= resp.status_code < 400, "Unable to access '{}' ({})".format(link_key, href)
