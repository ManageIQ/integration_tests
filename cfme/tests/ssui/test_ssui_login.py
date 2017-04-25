import pytest

from utils.appliance import get_or_create_current_appliance
from utils.appliance import ViaSSUI

pytestmark = pytest.mark.usefixtures('browser')


@pytest.mark.parametrize('context', [ViaSSUI])
def test_simple_login(context):
    appliance = get_or_create_current_appliance()

    with appliance.context.use(context):
        appliance.server.login()