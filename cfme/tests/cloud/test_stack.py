import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.cloud.stack import Stack
from utils import testgen
from utils.providers import setup_provider
from cfme.configure import settings  # NOQA
from cfme.web_ui import ButtonGroup, form_buttons

pytestmark = [
    pytest.mark.usefixtures('logged_in'),
    pytest.mark.ignore_stream("5.2", "5.3", "upstream"),
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(
        metafunc, ['ec2'], 'provisioning')
    metafunc.parametrize(argnames, argvalues, ids=idlist, scope='module')


@pytest.fixture
def provider_init(provider_key):
    """cfme/cloud/provider.py provider object."""
    setup_provider(provider_key)


def set_grid_view(name):
    bg = ButtonGroup(name)
    sel.force_navigate("my_settings_default_views")
    default_view = bg.active
    if(default_view != 'Grid View'):
        bg.choose('Grid View')
        sel.click(form_buttons.save)


@pytest.fixture(scope="function")
def stack(provider_init, provisioning):
    set_grid_view("Stacks")
    stackname = provisioning['stack']
    stack = Stack(stackname)
    return stack


def test_security_group_link(stack):
    stack.nav_to_security_group_link()


def test_parameters_link(stack):
    stack.nav_to_parameters_link()


@pytest.mark.meta(blockers=[1206016])
def test_outputs_link(stack):
    stack.nav_to_output_link()


def test_resources_link(stack):
    stack.nav_to_resources_link()


def test_edit_tags(stack):
    stack.edit_tags("Cost Center *", "Cost Center 001")


def test_delete(stack):
    stack.delete()
