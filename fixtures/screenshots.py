# -*- coding: utf-8 -*-
"""Taking screenshots inside tests!

If you want to take a screenshot inside your test, just do it like this:

.. code-block:: python
    def test_my_test(take_screenshot):
        # do something
        take_screenshot("Particular name for the screenshot")
        # do something else

"""
import pytest

from fixtures.artifactor_plugin import art_client
from utils.log import logger


@pytest.fixture(scope="function")
def take_screenshot(request):
    def _take_screenshot(name):
        test_name = request.node.location[2]
        test_location = request.node.location[0]
        logger.info("Taking a screenshot named {}".format(name))
        ss, ss_error = pytest.sel.take_screenshot()
        if ss_error:
            ss_error = ss_error.encode("base64")
        artifacts = {
            'name': name,
            'screenshot': ss,
            'screenshot_error': ss_error}

        art_client.fire_hook(
            'add_screenshot',
            test_name=test_name,
            test_location=test_location,
            artifacts=artifacts)

    return _take_screenshot
