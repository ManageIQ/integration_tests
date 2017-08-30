import fauxfactory
import pytest

from cfme.base.credential import Credential
from cfme.configure.access_control import Group, Role, User
from cfme.configure.configuration import Category, Tag
from cfme.web_ui import mixins
from utils.appliance.implementations.ui import navigate_to
from utils.log import logger


@pytest.yield_fixture(scope="session")
def category():
    """
        Returns random created category object
        Object can be used in all test run session
    """
    cg = Category(name=fauxfactory.gen_alpha(8).lower(),
                  description=fauxfactory.gen_alphanumeric(length=32),
                  display_name=fauxfactory.gen_alphanumeric(length=32))
    cg.create()
    yield cg
    cg.delete(False)


@pytest.yield_fixture(scope="session")
def tag(category):
    """
        Returns random created tag object
        Object can be used in all test run session
    """
    tag = Tag(name=fauxfactory.gen_alpha(8).lower(),
              display_name=fauxfactory.gen_alphanumeric(length=32),
              category=category)
    tag.create()
    yield tag
    tag.delete(False)


@pytest.yield_fixture(scope="module")
def role():
    """
        Returns role object used in test module
    """
    role = Role(
        name='role{}'.format(fauxfactory.gen_alphanumeric()),
        vm_restriction='None')
    role.create()
    yield role
    role.delete()


@pytest.yield_fixture(scope="module")
def group_with_tag(role, category, tag):
    """
        Returns group object with set up tag filter used in test module
    """
    group = Group(
        description='grp{}'.format(fauxfactory.gen_alphanumeric()),
        role=role.name,
        tag=[category.display_name, tag.display_name]
    )
    group.create()
    yield group
    group.delete()


@pytest.yield_fixture(scope="module")
def user_restricted(group_with_tag, new_credential):
    """
        Returns restricted user object assigned
        to group with tag filter used in test module
    """
    user = User(
        name='user{}'.format(fauxfactory.gen_alphanumeric()),
        credential=new_credential,
        email='xyz@redhat.com',
        group=group_with_tag,
        cost_center='Workload',
        value_assign='Database')
    user.create()
    yield user
    user.delete()


@pytest.fixture(scope="module")
def new_credential():
    """
        Returns credentials object used for new user in test module
    """
    # Todo remove .lower() for principal after 1486041 fix
    return Credential(
        principal='uid{}'.format(fauxfactory.gen_alphanumeric().lower()), secret='redhat')


# TODO should be updated(add_tag/remove_tag), after all used classes will support Taggable class
@pytest.fixture(scope='function')
def check_item_visibility(tag, user_restricted):
    def _check_item_visibility(vis_object, visibility_result):
        """
        Args:
            visibility_result: pass 'True' is item should be visible,
                               'False' if not
        """
        navigate_to(vis_object, 'Details')
        if visibility_result:
            mixins.add_tag(tag)
        else:
            try:
                mixins.remove_tag(tag)
            except TypeError:
                logger.debug('Tag is already removed')
        actual_visibility = False
        with user_restricted:
            try:
                navigate_to(vis_object, 'Details')
                actual_visibility = True
            except Exception:
                logger.debug('Tagged item is not visible')
        assert actual_visibility == visibility_result
    return _check_item_visibility
