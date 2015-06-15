# -*- coding: utf-8 -*-

from cfme.fixtures import pytest_selenium as sel
from cfme.configure import about
from utils import version
from utils.log import logger
import pytest
import requests


@pytest.mark.sauce
@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2246"])
def test_about_links():
    sel.force_navigate('about')
    for link_key, link_loc in about.product_assistance.locators.items():
        # If its a dict to be ver-picked and the resulting loc is None
        if isinstance(link_loc, dict) and version.pick(link_loc) is None:
            logger.info("Skipping link '{}'; not present in this version".format(link_key))
            continue
        href = sel.get_attribute(link_loc, 'href')
        try:
            resp = requests.head(href, verify=False, timeout=20)
        except (requests.Timeout, requests.ConnectionError) as ex:
            pytest.fail(ex.message)

        assert 200 <= resp.status_code < 400, "Unable to access '{}' ({})".format(link_key, href)
