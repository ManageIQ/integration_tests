import fauxfactory
import pytest

from cfme.base.credential import Credential
from cfme.cloud.tenant import Tenant
from cfme.infrastructure.host import Host
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger


@pytest.fixture(scope="module")
def category(appliance):
    """
        Returns random created category object
        Object can be used in all test run session
    """

    cg = appliance.collections.categories.create(
        name=fauxfactory.gen_alpha(8).lower(),
        description=fauxfactory.gen_alphanumeric(length=32),
        display_name=fauxfactory.gen_alphanumeric(length=32)
    )
    yield cg
    appliance.server.login_admin()
    cg.delete_if_exists()


@pytest.fixture(scope="module")
def tag(category, appliance):
    """
        Returns random created tag object
        Object can be used in all test run session
    """
    tag = category.collections.tags.create(
        name=fauxfactory.gen_alpha(8).lower(),
        display_name=fauxfactory.gen_alphanumeric(length=32)
    )
    yield tag
    appliance.server.login_admin()
    tag.delete_if_exists()


@pytest.fixture(scope="module")
def role(appliance):
    """
        Returns role object used in test module
    """
    role = appliance.collections.roles.create(
        name=fauxfactory.gen_alphanumeric(start="role_"),
        vm_restriction='None')
    yield role
    appliance.server.login_admin()
    role.delete_if_exists()


@pytest.fixture(scope="module")
def group_with_tag(appliance, role, tag):
    """
        Returns group object with set up tag filter used in test module
    """
    group = appliance.collections.groups.create(
        description=fauxfactory.gen_alphanumeric(start="group_"),
        role=role.name,
        tag=([tag.category.display_name, tag.display_name], True)
    )
    yield group
    appliance.server.login_admin()
    group.delete_if_exists()


@pytest.fixture(scope="module")
def user_restricted(appliance, group_with_tag, new_credential):
    """
        Returns restricted user object assigned
        to group with tag filter used in test module
    """
    user = appliance.collections.users.create(
        name=fauxfactory.gen_alphanumeric(start="user_"),
        credential=new_credential,
        email='xyz@redhat.com',
        groups=[group_with_tag],
        cost_center='Workload',
        value_assign='Database')
    yield user
    appliance.server.login_admin()
    user.delete_if_exists()


@pytest.fixture(scope="module")
def new_credential():
    """
        Returns credentials object used for new user in test module
    """
    return Credential(
        principal=fauxfactory.gen_alphanumeric(start="uid"), secret='redhat')


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
            vis_object.add_tag(tag=tag, exists_check=True)
        else:
            if tag in vis_object.get_tags():
                vis_object.remove_tag(tag=tag)
        with user_restricted:
            try:
                if isinstance(vis_object, Host):
                    # need to remove the link to the provider from the host,
                    # so the navigation goes Compute -> Infrastructure -> Hosts, not Providers
                    vis_object.parent.filters.update({'provider': None})
                if isinstance(vis_object, Tenant):
                    # removing links to the provider so the navigation goes
                    # Compute -> Clouds -> Tenants, not Providers
                    vis_object.provider = None
                    vis_object.parent.filters.update({'provider': None})
                navigate_to(vis_object, 'Details')
                actual_visibility = True
            except Exception:
                logger.debug('Tagged item is not visible')
                actual_visibility = False

        assert actual_visibility == vis_expect

    return _check_item_visibility
