# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils import error
from cfme.utils.blockers import BZ
from cfme.utils.update import update

pytestmark = [pytest.mark.tier(3)]


@pytest.fixture(scope="module")
def collection(appliance):
    return appliance.collections.customization_templates


def test_customization_template_crud(collection):
    """Basic CRUD test for customization templates."""

    template_crud = collection.create(name=fauxfactory.gen_alphanumeric(8),
                                      description=fauxfactory.gen_alphanumeric(16),
                                      image_type='RHEL-6',
                                      script_type='Kickstart',
                                      script_data='Testing the script')

    with update(template_crud):
        template_crud.name = template_crud.name + "_update"
    collection.delete(False, template_crud)


def test_name_required_error_validation(collection):
    """Test to validate name in customization templates."""

    with error.expected('Name is required'):
        collection.create(
            name=None,
            description=fauxfactory.gen_alphanumeric(16),
            image_type='RHEL-6',
            script_type='Kickstart',
            script_data='Testing the script')


def test_type_required_error_validation(collection):
    """Test to validate type in customization templates."""

    with error.expected('Type is required'):
        collection.create(
            name=fauxfactory.gen_alphanumeric(8),
            description=fauxfactory.gen_alphanumeric(16),
            image_type='RHEL-6',
            script_type=None,
            script_data='Testing the script')


def test_pxe_image_type_required_error_validation(collection):
    """Test to validate pxe image type in customization templates."""

    with error.expected("Pxe_image_type can't be blank"):
        collection.create(
            name=fauxfactory.gen_alphanumeric(8),
            description=fauxfactory.gen_alphanumeric(16),
            image_type=None,
            script_type='Kickstart',
            script_data='Testing the script')


@pytest.mark.meta(blockers=[BZ(1449116, forced_streams=['5.7', '5.8'])])
def test_duplicate_name_error_validation(collection):
    """Test to validate duplication in customization templates."""

    name = fauxfactory.gen_alphanumeric(8)
    description = fauxfactory.gen_alphanumeric(16)
    template_name = collection.create(
        name=name,
        description=description,
        image_type='RHEL-6',
        script_type='Kickstart',
        script_data='Testing the script')

    with error.expected('Name has already been taken'):
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
