import pytest

from cfme.infrastructure import pxe
from utils.randomness import generate_random_string
from utils.update import update

pytestmark = [pytest.mark.usefixtures("logged_in")]


def test_system_image_type_crud():
    """Basic default LDAP group role RBAC test

    Validates expected menu and submenu names are present for default
    LDAP group roles

    """
    sys_image_type = pxe.SystemImageType(
        name=generate_random_string(size=8),
        provision_type='Vm')
    sys_image_type.create()
    with update(sys_image_type) as sys_image_type:
        sys_image_type.name = sys_image_type.name + "_update"
    sys_image_type.delete(cancel=False)
