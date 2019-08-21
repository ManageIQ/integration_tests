import pytest

from cfme import test_requirements

pytestmark = [pytest.mark.tier(2), test_requirements.custom_button]


def test_custom_group_on_generic_class_crud(appliance):
    pass


def test_custom_button_on_generic_class_crud(appliance):
    pass
