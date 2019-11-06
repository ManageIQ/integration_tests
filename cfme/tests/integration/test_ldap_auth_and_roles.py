import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import credentials
from cfme.utils.testgen import auth_groups
from cfme.utils.testgen import generate

pytest_generate_tests = generate(gen_func=auth_groups, auth_mode='ldap')


@pytest.mark.uncollect(reason='Needs to be fixed after menu removed')
@test_requirements.auth
@pytest.mark.tier(2)
def test_group_roles(request, temp_appliance_preconfig_long, group_name, group_data):
    """Basic default LDAP group role RBAC test

    Validates expected menu and submenu names are present for default
    LDAP group roles


    Polarion:
        assignee: jdupuy
        caseimportance: medium
        casecomponent: Auth
        initialEstimate: 1/4h
        tags: rbac
    """
    appliance = temp_appliance_preconfig_long
    request.addfinalizer(appliance.server.login_admin)

    # This should be removed but currently these roles are subject to a bug
    if group_name in ['evmgroup-administrator',
                      'evmgroup-approver',
                      'evmgroup-auditor',
                      'evmgroup-operator',
                      'evmgroup-security',
                      'evmgroup-support',
                      'evmgroup-user']:
        pytest.skip("This role currently fails this test")

    try:
        username = credentials[group_name]['username']
        password = credentials[group_name]['password']
    except KeyError:
        pytest.fail('No match in credentials file for group "{}"'.format(group_name))

    user = appliance.collections.users.simple_user(username, password)
    with user:
        navigate_to(appliance.server, 'LoggedIn')
    # assert set(menu.nav.visible_pages()) == set(group_data)
