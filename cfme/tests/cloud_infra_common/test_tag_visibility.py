import cfme.configure.access_control as ac
import fauxfactory
import pytest
from cfme import Credential, login
from cfme.common.vm import VM
from cfme.configure.configuration import Tag, Category
from utils import testgen


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.all_providers(metafunc, required_fields=['ownership_vm'])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.yield_fixture(scope="module")
def new_category():
    category = Category(name="tag_vis_" + fauxfactory.gen_alpha(8).lower(),
                        description="tag_vis_" + fauxfactory.gen_alphanumeric(),
                        display_name="tag_vis_" + fauxfactory.gen_alphanumeric())
    category.create()
    yield category
    category.delete(cancel=False)


@pytest.yield_fixture(scope="module")
def new_tag(new_category):
    category = Category(name=new_category.name, display_name=new_category.display_name)
    tag = Tag(name="tag_vis_" + fauxfactory.gen_alphanumeric().lower(),
              display_name="tag_vis_" + fauxfactory.gen_alphanumeric().lower(),
              category=category)
    tag.create()
    yield tag
    tag.delete(cancel=False)


@pytest.yield_fixture(scope="module")
def new_role():
    role = ac.Role(name='tag_vis_role_' + fauxfactory.gen_alphanumeric())
    role.create()
    yield role
    role.delete()


@pytest.yield_fixture(scope="module")
def new_group(new_tag, new_role):
    group = ac.Group(description='tag_vis_group_' + fauxfactory.gen_alphanumeric(),
                     role=new_role.name)
    group.create()
    group.edit_tags(new_tag.category.display_name + " *", new_tag.display_name)
    yield group
    group.delete()


def new_credential():
    return Credential(principal='uid' + fauxfactory.gen_alphanumeric(), secret='redhat')


@pytest.yield_fixture(scope="module")
def new_user(new_group):
    user = ac.User(name='user_' + fauxfactory.gen_alphanumeric(),
                   credential=new_credential(),
                   email='abc@redhat.com',
                   group=new_group)
    user.create()
    yield user
    login.login_admin()
    user.delete()


@pytest.yield_fixture(scope="module")
def tagged_vm(new_tag, setup_provider, provider):
    ownership_vm = provider.data['ownership_vm']
    tag_vm = VM.factory(ownership_vm, provider)
    tag_vm.add_tag(new_tag)
    yield tag_vm
    login.login_admin()
    tag_vm.remove_tag(new_tag)


@pytest.mark.tier(3)
def test_tag_vis_vm(request, setup_provider, provider, tagged_vm, new_user):
    with new_user:
        assert tagged_vm.exists, "vm not found"
