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

from cfme.fixtures.artifactor_plugin import fire_art_test_hook
from cfme.fixtures.pytest_store import store
from cfme.utils.browser import take_screenshot as take_browser_screenshot
from cfme.utils.log import logger


@pytest.fixture(scope="function")
def take_screenshot(request):
    item = request.node

    def _take_screenshot(name):
        logger.info("Taking a screenshot named {}".format(name))
        ss, ss_error = take_browser_screenshot()
        g_id = fauxfactory.gen_alpha(length=6)
        if ss:
            fire_art_test_hook(
                item, 'filedump',
                description="Screenshot {}".format(name), file_type="screenshot", mode="wb",
                contents_base64=True, contents=ss, display_glyph="camera",
                group_id="fix-screenshot-{}".format(g_id), slaveid=store.slaveid)
        if ss_error:
            fire_art_test_hook(
                item, 'filedump',
                description="Screenshot error {}".format(name), mode="w", contents_base64=False,
                contents=ss_error, display_type="danger",
                group_id="fix-screenshot-{}".format(g_id), slaveid=store.slaveid)

    return _take_screenshot
