import fauxfactory
import pytest

from cfme.base.credential import Credential
from cfme.configure.configuration.region_settings import Category, Tag
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger


@pytest.fixture(scope="session")
def category():
    """
        Returns random created category object
        Object can be used in all test run session
    """
    if BZ(1517285, forced_streams='5.9').blocks:
        display_name = 'test-{}'.format(fauxfactory.gen_alphanumeric(length=27))
    # display_name should be with max length of 32
    else:
        display_name = fauxfactory.gen_alphanumeric(length=32)
    cg = Category(name=fauxfactory.gen_alpha(8).lower(),
                  description=fauxfactory.gen_alphanumeric(length=32),
                  display_name=display_name)
    cg.create()
    yield cg
    cg.delete(False)


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="module")
def role(appliance):
    """
        Returns role object used in test module
    """
    role = appliance.collections.roles.create(
        name='role{}'.format(fauxfactory.gen_alphanumeric()),
        vm_restriction='None')
    yield role
    role.delete()


@pytest.fixture(scope="module")
def group_with_tag(appliance, role, category, tag):
    """
        Returns group object with set up tag filter used in test module
    """
    group = appliance.collections.groups.create(
        description='grp{}'.format(fauxfactory.gen_alphanumeric()),
        role=role.name,
        tag=([category.display_name, tag.display_name], True)
    )
    yield group
    group.delete()


@pytest.fixture(scope="module")
def user_restricted(appliance, group_with_tag, new_credential):
    """
        Returns restricted user object assigned
        to group with tag filter used in test module
    """
    user = appliance.collections.users.create(
        name='user{}'.format(fauxfactory.gen_alphanumeric()),
        credential=new_credential,
        email='xyz@redhat.com',
        groups=[group_with_tag],
        cost_center='Workload',
        value_assign='Database')
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


@pytest.fixture(scope='function')
def check_item_visibility(tag, user_restricted):
    def _check_item_visibility(vis_object, vis_expect):
        """
        Args:
            vis_object: the object with a tag to check
            vis_expect: bool, True if tag should be visible

        Returns: None
        """
        if vis_expect:
            vis_object.add_tag(tag=tag)
        else:
            tags = vis_object.get_tags()
            tag_assigned = any(
                object_tags.category.display_name == tag.category.display_name and
                object_tags.display_name == tag.display_name for object_tags in tags
            )
            if tag_assigned:
                vis_object.remove_tag(tag=tag)
        with user_restricted:
            try:
                navigate_to(vis_object, 'Details')
                actual_visibility = True
            except Exception:
                logger.debug('Tagged item is not visible')
                actual_visibility = False

        assert actual_visibility == vis_expect

    return _check_item_visibility
