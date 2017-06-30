import pytest
from utils.appliance import ViaSSUI

# https://github.com/pytest-dev/pytest/issues/2540
# the tuple is needed
@pytest.mark.use_context((ViaSSUI,))
def test_ssui_login(appliance):
    appliance.server.login()
