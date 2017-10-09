import pytest

from cfme import test_requirements
from cfme.common.vm import VM
from cfme.utils import testgen


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.all_providers(metafunc, required_fields=['cap_and_util'])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


pytestmark = [test_requirements.tag]


@pytest.yield_fixture(scope="module")
def tagged_vm(tag, has_no_providers_modscope, setup_provider_modscope, provider):
    ownership_vm = provider.data.cap_and_util.capandu_vm
    tag_vm = VM.factory(ownership_vm, provider)
    tag_vm.add_tag(tag=tag)
    yield tag_vm
    tag_vm.appliance.server.login_admin()
    tag_vm.remove_tag(tag=tag)


@pytest.mark.tier(3)
def test_tag_vis_vm(tagged_vm, user_restricted):
    with user_restricted:
        assert tagged_vm.exists, "vm not found"
