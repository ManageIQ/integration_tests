import pytest

from cfme.infrastructure import pxe
from utils.randomness import generate_random_string
from utils.update import update

pytestmark = [pytest.mark.usefixtures("logged_in")]


def test_customization_template_crud():
    """
    Basic CRUD test for customization templates.
    """
    template_crud = pxe.CustomizationTemplate(
        name=generate_random_string(size=8),
        description=generate_random_string(size=16),
        image_type='RHEL-6',
        script_type='Kickstart',
        script_data='Testing the script')

    template_crud.create()
    with update(template_crud) as template_crud:
        template_crud.name = template_crud.name + "_update"
    template_crud.delete(cancel=False)
