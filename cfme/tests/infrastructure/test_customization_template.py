# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.infrastructure import pxe
from utils import error
from utils.blockers import BZ
from utils.update import update

pytestmark = [pytest.mark.usefixtures("logged_in")]


def test_customization_template_crud():
    """Basic CRUD test for customization templates."""
    template_crud = pxe.CustomizationTemplate(
        name=fauxfactory.gen_alphanumeric(8),
        description=fauxfactory.gen_alphanumeric(16),
        image_type='RHEL-6',
        script_type='Kickstart',
        script_data='Testing the script')

    template_crud.create()
    with update(template_crud):
        template_crud.name = template_crud.name + "_update"
    template_crud.delete(cancel=False)


def test_name_required_error_validation():
    """Test to validate name in customization templates."""
    template_name = pxe.CustomizationTemplate(
        name=None,
        description=fauxfactory.gen_alphanumeric(16),
        image_type='RHEL-6',
        script_type='Kickstart',
        script_data='Testing the script')

    with error.expected('Name is required'):
        template_name.create()


def test_type_required_error_validation():
    """Test to validate type in customization templates."""
    template_name = pxe.CustomizationTemplate(
        name=fauxfactory.gen_alphanumeric(8),
        description=fauxfactory.gen_alphanumeric(16),
        image_type='RHEL-6',
        script_type='<Choose>',
        script_data='Testing the script')

    with error.expected('Type is required'):
        template_name.create()


def test_pxe_image_type_required_error_validation():
    """Test to validate pxe image type in customization templates."""
    template_name = pxe.CustomizationTemplate(
        name=fauxfactory.gen_alphanumeric(8),
        description=fauxfactory.gen_alphanumeric(16),
        image_type='<Choose>',
        script_type='Kickstart',
        script_data='Testing the script')

    with error.expected("Pxe_image_type can't be blank"):
        template_name.create()


@pytest.mark.meta(
    blockers=[
        BZ(1092951, ignore_bugs=[1083198])
    ]
)
def test_duplicate_name_error_validation():
    """Test to validate duplication in customization templates."""
    template_name = pxe.CustomizationTemplate(
        name=fauxfactory.gen_alphanumeric(8),
        description=fauxfactory.gen_alphanumeric(16),
        image_type='RHEL-6',
        script_type='Kickstart',
        script_data='Testing the script')

    template_name.create()
    with error.expected('Name has already been taken'):
        template_name.create()
    template_name.delete(cancel=False)


@pytest.mark.xfail(message='http://cfme-tests.readthedocs.org/guides/gotchas.html#'
    'selenium-is-not-clicking-on-the-element-it-says-it-is')
def test_name_max_character_validation():
    """Test to validate name with maximum characters in customization templates."""
    template_name = pxe.CustomizationTemplate(
        name=fauxfactory.gen_alphanumeric(256),
        description=fauxfactory.gen_alphanumeric(16),
        image_type='RHEL-6',
        script_type='Kickstart',
        script_data='Testing the script')

    with error.expected('Name is required'):
        template_name.create()
    template_name.delete(cancel=False)
