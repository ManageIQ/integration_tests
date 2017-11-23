# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.utils import error, version
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


@pytest.mark.uncollectif(lambda: version.current_version() < '5.9')
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


@pytest.mark.xfail(message='http://cfme-tests.readthedocs.org/guides/gotchas.html#'
                           'selenium-is-not-clicking-on-the-element-it-says-it-is')
def test_name_max_character_validation(collection):
    """Test to validate name with maximum characters in customization templates."""

    with error.expected('Name is required'):
        template_name = collection.create(
            name=fauxfactory.gen_alphanumeric(256),
            description=fauxfactory.gen_alphanumeric(16),
            image_type='RHEL-6',
            script_type='Kickstart',
            script_data='Testing the script')
    collection.delete(False, template_name)
