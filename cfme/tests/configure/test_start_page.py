import pytest
import fauxfactory

from cfme.base.credential import Credential
from cfme.configure.settings import Visual
from cfme.configure.access_control import Role, Group, User
from cfme.utils.appliance.implementations.ui import navigate_to


faux_value = fauxfactory.gen_alphanumeric()
pytestmark = pytest.mark.usefixtures('browser')


def create_role():
    role = Role(name='test{}'.format(faux_value))
    role.create()


def create_group():
    role = 'test' + faux_value
    group = Group(description='test{}'.format(faux_value), role=role)
    group.create()


def create_user():
    group_user = Group('test{}'.format(faux_value))
    username = 'test{}'.format(faux_value.lower())
    password = 'test'
    cred = Credential(principal=username, secret=password)
    user = User(name='test{}'.format(faux_value),
                credential=cred, group=group_user)

    user.create()
    return user


def user_login(user, appliance):
    login_page = navigate_to(appliance.server, 'LoginScreen')
    login_page.log_in(user)


def set_landing_page(user, values, appliance):
    # This list contains the list of pages which show some error or alerts after login.
    # TODO remove all these pages when BZ is closed.
    page_list = ['Bottlenecks', 'Automate Log', 'Compute / Containers / Containers']
    for value in values:
        view = navigate_to(Visual, 'All')
        if (view.visualstartpage.show_at_login.fill(value.text) and
                not any(substring in value.text for substring in page_list)):
            view.save.click()
            user_login(user, appliance)
        logged_in_page = navigate_to(appliance.server, 'LoggedIn')
        if not logged_in_page.is_displayed:
            return False
    return True


def test_start_page_rbac(appliance):
    """
        This test checks the functioning of the landing page; 'Start at Login'
        option on 'Visual' tab of setting page for custom role based users.
    """
    create_role()
    create_group()
    user = create_user()
    appliance.server.logout()
    user_login(user, appliance)
    view = navigate_to(Visual, 'All')
    values = view.visualstartpage.show_at_login.all_options
    assert set_landing_page(user, values, appliance)
