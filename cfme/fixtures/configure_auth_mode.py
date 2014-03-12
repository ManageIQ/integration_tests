
import pytest
from utils.conf import cfme_data, credentials
from cfme.configure import configuration


@pytest.yield_fixture(scope='module')  # IGNORE:E1101
def configure_ldap_auth_mode():
    """Configure LDAP authentication mode"""
    server_data = cfme_data['auth_modes']['ldap_server']
    configuration.set_auth_mode(**server_data)
    yield
    configuration.set_auth_mode(mode='database')


@pytest.yield_fixture(scope='module')  # IGNORE:E1101
def configure_aws_iam_auth_mode():
    """Configure AWS IAM authentication mode"""
    aws_iam_data = dict(cfme_data['auth_modes']['aws_iam'])
    aws_iam_creds = credentials[aws_iam_data.pop('credentials')]
    aws_iam_data['access_key'] = aws_iam_creds['username']
    aws_iam_data['secret_key'] = aws_iam_creds['password']
    configuration.set_auth_mode(**aws_iam_data)
    yield
    configuration.set_auth_mode(mode='database')
