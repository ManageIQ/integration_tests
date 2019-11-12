import pytest
import requests

from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.ignore_stream("5.11")]


@pytest.mark.tier(3)
def test_verify_rss_links(appliance):
    """
    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: WebUI
    """
    view = navigate_to(appliance.server, 'RSS')
    for row in view.table.rows():
        url = row[3].text
        req = requests.get(url, verify=False)
        assert 200 <= req.status_code < 400, "The url {} seems malformed".format(repr(url))
