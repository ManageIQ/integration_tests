# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.infrastructure.pxe import SystemImageType
from cfme.utils import error
from cfme.utils.update import update

pytestmark = [pytest.mark.tier(3)]


def test_system_image_type_crud(appliance):
    """
    Tests a System Image Type using CRUD operations.
    """
    collection = appliance.collections.system_image_types
    sys_image_type = collection.create(
        name=fauxfactory.gen_alphanumeric(8),
        provision_type=SystemImageType.VM_OR_INSTANCE)
    with update(sys_image_type):
        sys_image_type.name = sys_image_type.name + "_update"
    sys_image_type.delete(cancel=False)


def test_duplicate_name_error_validation(appliance):
    """
    Tests a System Image for duplicate name.
    """
    collection = appliance.collections.system_image_types
    name = fauxfactory.gen_alphanumeric(8)
    sys_image_type = collection.create(
        name=name,
        provision_type=SystemImageType.VM_OR_INSTANCE)
    with error.expected('Name has already been taken'):
        collection.create(
            name=name,
            provision_type=SystemImageType.VM_OR_INSTANCE)
    sys_image_type.delete(cancel=False)


def test_name_required_error_validation(appliance):
    """
    Tests a System Image with no name.
    """
    collection = appliance.collections.system_image_types
    with error.expected('Name is required'):
        collection.create(
            name=None,
            provision_type=SystemImageType.VM_OR_INSTANCE)

# Commenting the maximum charater validation due to
# http://cfme-tests.readthedocs.org/guides/gotchas.html#
#    selenium-is-not-clicking-on-the-element-it-says-it-is
# def test_name_max_character_validation():
#    """
#    Tests a System Image name with max characters.
#    """
#    sys_image_type = SystemImageType(
#        name=fauxfactory.gen_alphanumeric(256),
#        provision_type='Vm')
#    sys_image_type.create()
#    sys_image_type.delete(cancel=False)
