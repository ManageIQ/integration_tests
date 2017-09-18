import pytest

from cfme.base.ssui import SSUIBaseLoggedInPage
from cfme.utils.appliance import get_or_create_current_appliance
from cfme.utils.appliance import ViaSSUI
from cfme.utils.version import current_version


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
@pytest.mark.parametrize('context', [ViaSSUI])
def test_ssui_login(context):
    appliance = get_or_create_current_appliance()
    with appliance.context.use(context):
        appliance.server.login()
        logged_in_page = appliance.browser.create_view(SSUIBaseLoggedInPage)
        assert logged_in_page.is_displayed
        logged_in_page.logout()
