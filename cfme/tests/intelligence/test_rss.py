# -*- coding: utf-8 -*-
import pytest
import requests

from cfme.base.ui import Server
from cfme.web_ui import Table
from utils.appliance.implementations.ui import navigate_to

rss_table = Table("//div[@id='tab_div']/table", header_offset=1)


@pytest.mark.tier(3)
def test_verify_rss_links():
    navigate_to(Server, 'RSS')
    for row in rss_table.rows():
        url = pytest.sel.text(row["feed_url"]).strip()
        req = requests.get(url, verify=False)
        assert 200 <= req.status_code < 400, "The url {} seems malformed".format(repr(url))
