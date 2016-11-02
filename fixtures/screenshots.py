# -*- coding: utf-8 -*-
"""Taking screenshots inside tests!

If you want to take a screenshot inside your test, just do it like this:

.. code-block:: python

    def test_my_test(take_screenshot):
        # do something
        take_screenshot("Particular name for the screenshot")
        # do something else

"""
import fauxfactory
import pytest

from fixtures.artifactor_plugin import art_client
from utils.log import logger


@pytest.fixture(scope="function")
def take_screenshot(request):
    def _take_screenshot(name):
        from fixtures.artifactor_plugin import SLAVEID
        test_name = request.node.location[2]
        test_location = request.node.location[0]
        logger.info("Taking a screenshot named {}".format(name))
        ss, ss_error = pytest.sel.take_screenshot()
        g_id = fauxfactory.gen_alpha(length=6)

        if ss:
            art_client.fire_hook('filedump', test_location=test_location, test_name=test_name,
                description="Screenshot {}".format(name), file_type="screenshot", mode="wb",
                contents_base64=True, contents=ss, display_glyph="camera",
                group_id="fix-screenshot-{}".format(g_id), slaveid=SLAVEID)
        if ss_error:
            art_client.fire_hook('filedump', test_location=test_location, test_name=test_name,
                description="Screenshot error {}".format(name), mode="w", contents_base64=False,
                contents=ss_error, display_type="danger",
                group_id="fix-screenshot-{}".format(g_id), slaveid=SLAVEID)

    return _take_screenshot
