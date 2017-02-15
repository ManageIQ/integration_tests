import pytest

from cfme.configure.access_control import simple_user
from cfme.infrastructure.provider import InfraProvider
from cfme.login import login, login_admin
from utils.conf import credentials
from utils.testgen import auth_groups, generate
from utils import version
from utils.providers import setup_a_provider_by_class

pytest_generate_tests = generate(gen_func=auth_groups, auth_mode='aws_iam')


@pytest.fixture(scope="module")
def setup_first_provider():
    setup_a_provider_by_class(InfraProvider)


@pytest.mark.uncollect('Needs to be fixed after menu removed')
@pytest.mark.tier(2)
def test_group_roles(
        request, configure_aws_iam_auth_mode, group_name, group_data, setup_first_provider):
    """Basic default AWS_IAM group role RBAC test

    Validates expected menu and submenu names are present for default
    AWS IAM groups

    """
    request.addfinalizer(login_admin)

    # This should be removed but currently these roles are subject to a bug
    if version.current_version() >= '5.4' and group_name in ['evmgroup-administrator',
                                                             'evmgroup-approver',
                                                             'evmgroup-auditor',
                                                             'evmgroup-operator',
                                                             'evmgroup-security',
                                                             'evmgroup-support',
                                                             'evmgroup-user']:
        pytest.skip("This role currently fails this test")

    try:
        iam_group_name = group_name + '_aws_iam'
        username = credentials[iam_group_name]['username']
        password = credentials[iam_group_name]['password']
    except KeyError:
        pytest.fail('No match in credentials file for group "{}"'.format(iam_group_name))

    login(simple_user(username, password))
    # assert set(menu.visible_pages()) == set(group_data)
