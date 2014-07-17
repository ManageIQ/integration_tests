import pytest
from utils.randomness import generate_random_string
from utils.update import update
import utils.error as error
import cfme.tests.automate as ta

pytestmark = [pytest.mark.usefixtures("logged_in")]


@pytest.fixture(scope='module')
def make_class():
    return ta.make_class()


@pytest.fixture
def an_instance(make_class):
    return ta.an_instance(make_class)


def test_instance_crud(an_instance):
    an_instance.create()
    origname = an_instance.name
    with update(an_instance):
        an_instance.name = generate_random_string(8)
        an_instance.description = "updated"
    with update(an_instance):
        an_instance.name = origname
    an_instance.delete()
    assert not an_instance.exists()


def test_duplicate_disallowed(an_instance):
    an_instance.create()
    with error.expected("Name has already been taken"):
        an_instance.create()
