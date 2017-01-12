# -*- coding: utf-8 -*-
import requests
import pytest

from cfme.base.ui import Server
from cfme.fixtures import pytest_selenium as sel
from cfme.configure import about
from utils import version
from utils.appliance.implementations.ui import navigate_to
from utils.log import logger


@pytest.mark.tier(3)
@pytest.mark.sauce
@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:2246"])
@pytest.mark.meta(blockers=[1272618])
def test_about_links():
    if version.current_version() < '5.7':
        navigate_to(Server, 'About')
    else:
        navigate_to(Server, 'Documentation')

    for link_key, link_loc in about.product_assistance.locators.items():
        # If its a dict to be ver-picked and the resulting loc is None
        if isinstance(link_loc, dict) and version.pick(link_loc) is None:
            logger.info("Skipping link %s; not present in this version", link_key)
            continue
        href = sel.get_attribute(link_loc, 'href')
        try:
            resp = requests.head(href, verify=False, timeout=20)
        except (requests.Timeout, requests.ConnectionError) as ex:
            pytest.fail(str(ex))

        assert 200 <= resp.status_code < 400, "Unable to access '{}' ({})".format(link_key, href)
