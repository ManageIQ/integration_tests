from __future__ import unicode_literals
import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.cloud.stack import Stack
from utils import testgen
from cfme.configure import settings  # NOQA
from cfme.web_ui import ButtonGroup, form_buttons

pytestmark = [
    pytest.mark.ignore_stream("upstream"),
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['ec2'])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope='module')


def set_grid_view(name):
    bg = ButtonGroup(name)
    sel.force_navigate("my_settings_default_views")
    default_view = bg.active
    if(default_view != 'Grid View'):
        bg.choose('Grid View')
        sel.click(form_buttons.save)


@pytest.fixture(scope="function")
def stack(setup_provider, provider, provisioning):
    set_grid_view("Stacks")
    stackname = provisioning['stack']
    stack = Stack(stackname)
    return stack


@pytest.mark.tier(3)
def test_security_group_link(stack):
    stack.nav_to_security_group_link()


@pytest.mark.tier(3)
def test_parameters_link(stack):
    stack.nav_to_parameters_link()


@pytest.mark.tier(3)
def test_outputs_link(stack):
    stack.nav_to_output_link()


@pytest.mark.tier(3)
def test_resources_link(stack):
    stack.nav_to_resources_link()


@pytest.mark.tier(3)
def test_edit_tags(stack):
    stack.edit_tags("Cost Center *", "Cost Center 001")


@pytest.mark.tier(3)
def test_delete(stack):
    stack.delete()
