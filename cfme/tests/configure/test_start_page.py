import pytest
import fauxfactory

from cfme.base.credential import Credential
from cfme.configure.settings import Visual
from cfme.configure.access_control import Role, Group, User
from cfme.utils.appliance.implementations.ui import navigate_to


faux_value = fauxfactory.gen_alphanumeric()
pytestmark = pytest.mark.usefixtures('browser')


def get_landing_page():
    view = navigate_to(Visual, 'All')
    landing_pages = view.visualstartpage.show_at_login.all_options
    start_page = []
    for landing_page in landing_pages:
        start_page.append(landing_page.text)
    return start_page


@pytest.yield_fixture(scope="module")
def rbac_user(appliance):
    role = Role(name='test{}'.format(faux_value))
    role.create()
    role_name = 'test' + faux_value
    group = Group(description='test{}'.format(faux_value), role=role_name)
    group.create()
    group_user = Group('test{}'.format(faux_value))
    username = 'test{}'.format(faux_value.lower())
    password = 'test'
    cred = Credential(principal=username, secret=password)
    user = User(name='test{}'.format(faux_value),
                credential=cred, group=group_user)
    user.create()
    appliance.server.logout()
    user_login(user, appliance)
    view = navigate_to(Visual, 'All')
    values = view.visualstartpage.show_at_login.all_options
    yield user, values
    appliance.server.logout()
    login_page = navigate_to(appliance.server, 'LoginScreen')
    login_page.login_admin()
    user.delete()
    group.delete()
    role.delete()


def user_login(user, appliance):
    login_page = navigate_to(appliance.server, 'LoginScreen')
    login_page.log_in(user)


def set_landing_page_rbac(user, values, appliance):
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


def set_landing_page_admin(value, appliance):
    # This list contains the list of pages which show some error or alerts after login.
    # TODO remove all these pages when BZ is closed.
    page_list = ['Bottlenecks', 'Automate Log', 'Compute / Containers / Containers']
    view = navigate_to(Visual, 'All')
    if (view.visualstartpage.show_at_login.fill(value) and
            not any(substring in value for substring in page_list)):
        view.save.click()
        login_page = navigate_to(appliance.server, 'LoginScreen')
        login_page.login_admin()
        logged_in_page = navigate_to(appliance.server, 'LoggedIn')
        if not logged_in_page.is_displayed:
            return False
    return True


def test_start_page_rbac(appliance, rbac_user):
    """
        This test checks the functioning of the landing page; 'Start at Login'
        option on 'Visual' tab of setting page for custom role based users. This test case doesn't
        check the exact page but verifies that all the landing page options works properly.
    """
    user, start_page = rbac_user
    assert set_landing_page_rbac(user, start_page, appliance)


@pytest.mark.parametrize('start_page', get_landing_page(), scope="module")
def test_strat_page_admin(start_page, appliance):
    """
        This test checks the functioning of the landing page; 'Start at Login'
        option on 'Visual' tab of setting page for administrator. This test case doesn't
        check the exact page but verifies that all the landing page options works properly.
    """
    assert set_landing_page_admin(start_page, appliance)
