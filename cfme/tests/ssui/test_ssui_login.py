from __future__ import absolute_import
import pytest

from utils.appliance import get_or_create_current_appliance
from utils.appliance import ViaSSUI


@pytest.mark.parametrize('context', [ViaSSUI])
def test_ssui_login(context):
    appliance = get_or_create_current_appliance()

    with appliance.context.use(context):
        appliance.server.login()
