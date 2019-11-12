import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.pxe import SystemImageType
from cfme.utils.update import update

pytestmark = [test_requirements.general_ui, pytest.mark.tier(3)]


@pytest.mark.sauce
def test_system_image_type_crud(appliance):
    """
    Tests a System Image Type using CRUD operations.

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/10h
    """
    collection = appliance.collections.system_image_types
    sys_image_type = collection.create(
        name=fauxfactory.gen_alphanumeric(8),
        provision_type=SystemImageType.VM_OR_INSTANCE)
    with update(sys_image_type):
        sys_image_type.name = sys_image_type.name + "_update"
    sys_image_type.delete(cancel=False)


def test_system_image_duplicate_name_error_validation(appliance):
    """
    Tests a System Image for duplicate name.

    Polarion:
        assignee: pvala
        initialEstimate: 1/4h
        casecomponent: WebUI
    """
    collection = appliance.collections.system_image_types
    name = fauxfactory.gen_alphanumeric(8)
    sys_image_type = collection.create(
        name=name,
        provision_type=SystemImageType.VM_OR_INSTANCE)
    error_message = (
        "Name has already been taken"
        if appliance.version < "5.10"
        else "Name is not unique within region 0"
    )
    with pytest.raises(Exception, match=error_message):
        collection.create(
            name=name,
            provision_type=SystemImageType.VM_OR_INSTANCE)
    sys_image_type.delete(cancel=False)


def test_name_required_error_validation_system_image(appliance):
    """
    Tests a System Image with no name.

    Polarion:
        assignee: pvala
        initialEstimate: 1/4h
        casecomponent: WebUI
    """
    collection = appliance.collections.system_image_types
    with pytest.raises(Exception, match='Name is required'):
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


def test_system_image_type_selective_delete(appliance):
    """
    Tests System Image Type for delete operation using select option on All page.

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/12h
    """
    collection = appliance.collections.system_image_types
    sys_image_type1 = collection.create(
        name=fauxfactory.gen_alphanumeric(8),
        provision_type=SystemImageType.VM_OR_INSTANCE)
    sys_image_type2 = collection.create(
        name=fauxfactory.gen_alphanumeric(8),
        provision_type=SystemImageType.VM_OR_INSTANCE)
    collection.delete(False, sys_image_type1, sys_image_type2)
