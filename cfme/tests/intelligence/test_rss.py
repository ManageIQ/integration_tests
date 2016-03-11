# -*- coding: utf-8 -*-
import pytest
import requests

from cfme.web_ui.tables import Table, Ordinary


rss_table = Table(Ordinary("//div[@id='tab_div']/table", header_offset=1))


def test_verify_rss_links():
    pytest.sel.force_navigate("rss")
    for row in rss_table.rows():
        url = pytest.sel.text(row["feed_url"]).strip()
        req = requests.get(url, verify=False)
        assert 200 <= req.status_code < 400, "The url {} seems malformed".format(repr(url))
