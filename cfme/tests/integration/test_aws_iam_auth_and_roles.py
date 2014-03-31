import pytest

from cfme.login import force_login_user
from utils.conf import credentials
from utils.testgen import auth_groups, generate

pytest_generate_tests = generate(auth_groups, auth_mode='aws_iam')


def test_group_roles(configure_aws_iam_auth_mode, group_name, group_data, visible_pages):
    """Basic default AWS_IAM group role RBAC test

    Validates expected menu and submenu names are present for default
    AWS IAM groups

    """
    try:
        iam_group_name = group_name + '_aws_iam'
        username = credentials[iam_group_name]['username']
        password = credentials[iam_group_name]['password']
    except KeyError:
        pytest.fail('No match in credentials file for group "%s"' % iam_group_name)

    force_login_user(username, password)
    assert visible_pages() == group_data
