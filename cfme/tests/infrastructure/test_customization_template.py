import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.pxe import SystemImageType
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update

pytestmark = [
    test_requirements.provision,
    pytest.mark.tier(3)
]


@pytest.fixture(scope="module")
def collection(appliance):
    return appliance.collections.customization_templates


@pytest.fixture(scope="module")
def image_type(appliance):
    image_type = appliance.collections.system_image_types.create(
        name=fauxfactory.gen_alphanumeric(8), provision_type=SystemImageType.VM_OR_INSTANCE)
    yield image_type
    image_type.delete()


@pytest.mark.sauce
@pytest.mark.parametrize("script_type", ["Kickstart", "Sysprep", "CloudInit"],
                         ids=["kickstart", "sysprep", "cloudinit"])
def test_customization_template_crud(collection, script_type, image_type):
    """Basic CRUD test for customization templates.

    Polarion:
        assignee: jhenner
        casecomponent: WebUI
        initialEstimate: 1/15h
    """

    template_crud = collection.create(name="{}_{}".format(script_type,
                                                          fauxfactory.gen_alphanumeric(4)),
                                      description=fauxfactory.gen_alphanumeric(16),
                                      image_type=image_type.name,
                                      script_type=script_type,
                                      script_data='Testing the script')
    with update(template_crud):
        template_crud.name = template_crud.name + "_update"
    collection.delete(False, template_crud)


def test_name_required_error_validation_cust_template(collection):
    """Test to validate name in customization templates.

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: WebUI
    """

    with pytest.raises(Exception, match='Name is required'):
        collection.create(
            name=None,
            description=fauxfactory.gen_alphanumeric(16),
            image_type='RHEL-6',
            script_type='Kickstart',
            script_data='Testing the script')


def test_type_required_error_validation(collection):
    """Test to validate type in customization templates.

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: WebUI
    """

    with pytest.raises(Exception, match='Type is required'):
        collection.create(
            name=fauxfactory.gen_alphanumeric(8),
            description=fauxfactory.gen_alphanumeric(16),
            image_type='RHEL-6',
            script_type=None,
            script_data='Testing the script')


def test_pxe_image_type_required_error_validation(collection):
    """Test to validate pxe image type in customization templates.

    Polarion:
        assignee: jhenner
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/6h
        upstream: yes
    """

    with pytest.raises(Exception, match="Pxe_image_type can't be blank"):
        collection.create(
            name=fauxfactory.gen_alphanumeric(8),
            description=fauxfactory.gen_alphanumeric(16),
            image_type=None,
            script_type='Kickstart',
            script_data='Testing the script')


def test_cust_template_duplicate_name_error_validation(collection):
    """Test to validate duplication in customization templates.

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: WebUI
    """

    name = fauxfactory.gen_alphanumeric(8)
    description = fauxfactory.gen_alphanumeric(16)
    template_name = collection.create(
        name=name,
        description=description,
        image_type='RHEL-6',
        script_type='Kickstart',
        script_data='Testing the script')

    with pytest.raises(Exception, match='Name has already been taken'):
        collection.create(
            name=name,
            description=description,
            image_type='RHEL-6',
            script_type='Kickstart',
            script_data='Testing the script')
    collection.delete(False, template_name)


def test_name_max_character_validation(collection):
    """Test to validate name with maximum characters in customization templates.
       Max length is controlled by UI elements - we are not allowed to input more than we should
       Opens template details to verify that extra symbols were cut

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: WebUI
    """
    template_name = collection.create(
        name=fauxfactory.gen_alphanumeric(256),
        description=fauxfactory.gen_alphanumeric(16),
        image_type='RHEL-6',
        script_type='Kickstart',
        script_data='Testing the script')
    template_name.name = template_name.name[:255]
    view = navigate_to(template_name, 'Details')
    assert len(view.entities.basic_information.get_text_of('Name')) < 256
    collection.delete(False, template_name)


def test_customization_template_copy(collection):
    """
    Test to check the copy operation of customization templates.

    Polarion:
        assignee: jhenner
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/15h
    """
    template_crud = collection.create(name=fauxfactory.gen_alphanumeric(8),
                                      description=fauxfactory.gen_alphanumeric(16),
                                      image_type='RHEL-6',
                                      script_type='Kickstart',
                                      script_data='Testing the script')
    copy_template_crud = template_crud.copy()
    collection.delete(False, template_crud, copy_template_crud)
