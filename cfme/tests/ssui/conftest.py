import pytest

from fixtures.pytest_store import store
from utils import browser


def revert_to_default():
    store.current_appliance.mode = "default"
    browser.quit()


@pytest.fixture(scope="module", autouse=True)
def set_ssui_mode(request):
    store.current_appliance.mode = "ssui"
