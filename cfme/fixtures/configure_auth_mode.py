import pytest

from utils.conf import cfme_data, credentials
from utils.ext_auth import disable_external_auth_ipa, disable_external_auth_openldap, \
    setup_external_auth_ipa, setup_external_auth_openldap
from cfme.configure import configuration
from cfme.login import login_admin


@pytest.fixture(scope='session')
def available_auth_modes():
    return cfme_data.get('auth_modes', {}).keys()


@pytest.yield_fixture(scope='module')
def configure_ldap_auth_mode(browser, available_auth_modes):
    """Configure LDAP authentication mode"""
    if 'miq_ldap' in available_auth_modes:
        server_data = cfme_data.get('auth_modes', {})['miq_ldap']
        configuration.set_auth_mode(**server_data)
        yield
        login_admin()
        configuration.set_auth_mode(mode='database')
    else:
        yield


@pytest.yield_fixture(scope='module')
def configure_openldap_auth_mode(browser, available_auth_modes):
    """Configure LDAP authentication mode"""
    if 'miq_openldap' in available_auth_modes:
        server_data = cfme_data.get('auth_modes', {})['miq_openldap']
        configuration.set_auth_mode(**server_data)
        yield
        login_admin()
        configuration.set_auth_mode(mode='database')
    else:
        yield


@pytest.yield_fixture(scope='module')
def configure_openldap_auth_mode_default_groups(browser, available_auth_modes):
    """Configure LDAP authentication mode"""
    if 'miq_openldap' in available_auth_modes:
        server_data = cfme_data.get('auth_modes', {})['miq_openldap']
        server_data['get_groups'] = False
        server_data['default_groups'] = 'EvmRole-user'
        configuration.set_auth_mode(**server_data)
        yield
        login_admin()
        configuration.set_auth_mode(mode='database')
    else:
        yield


@pytest.yield_fixture(scope='module')
def configure_aws_iam_auth_mode(browser, available_auth_modes):
    """Configure AWS IAM authentication mode"""
    if 'miq_aws_iam' in available_auth_modes:
        aws_iam_data = dict(cfme_data.get('auth_modes', {})['miq_aws_iam'])
        aws_iam_creds = credentials[aws_iam_data.pop('credentials')]
        aws_iam_data['access_key'] = aws_iam_creds['username']
        aws_iam_data['secret_key'] = aws_iam_creds['password']
        configuration.set_auth_mode(**aws_iam_data)
        yield
        login_admin()
        configuration.set_auth_mode(mode='database')
    else:
        yield


@pytest.fixture()
def configure_auth(request, auth_mode):
    data = cfme_data['auth_modes'].get(auth_mode, {})
    if auth_mode == 'ext_ipa':
        request.addfinalizer(disable_external_auth_ipa)
        setup_external_auth_ipa(**data)
    elif auth_mode == 'ext_openldap':
        request.addfinalizer(disable_external_auth_openldap)
        setup_external_auth_openldap(**data)
    elif auth_mode in ['miq_openldap', 'miq_ldap']:
        configuration.set_auth_mode(**data)
        request.addfinalizer(login_admin)
        request.addfinalizer(configuration.setup_authmode_database)
    elif auth_mode == 'miq_aws_iam':
        aws_iam_creds = credentials[data.pop('credentials')]
        data['access_key'] = aws_iam_creds['username']
        data['secret_key'] = aws_iam_creds['password']
        configuration.set_auth_mode(**data)
        request.addfinalizer(login_admin)
        request.addfinalizer(configuration.setup_authmode_database)
    else:
        pytest.skip("auth_mode specified is not a expected value for cfme_auth tests")
