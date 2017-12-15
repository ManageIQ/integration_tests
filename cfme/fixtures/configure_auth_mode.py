import pytest

from cfme.utils.conf import cfme_data, credentials
from cfme.utils.appliance import current_appliance
from cfme.utils.ext_auth import (disable_external_auth_ipa, disable_external_auth_openldap,
    setup_external_auth_ipa, setup_external_auth_openldap)


@pytest.fixture(scope='session')
def available_auth_modes():
    return cfme_data.get('auth_modes', {}).keys()


@pytest.yield_fixture(scope='module')
def configure_ldap_auth_mode(browser, available_auth_modes):
    """Configure LDAP authentication mode"""
    if 'miq_ldap' in available_auth_modes:
        auth_mode = current_appliance.server.authentication
        server_data = cfme_data.get('auth_modes', {})['miq_ldap']
        auth_mode.set_auth_mode(**server_data)
        yield
        current_appliance.server.login_admin()
        auth_mode.set_auth_mode()
    else:
        yield


@pytest.yield_fixture(scope='module')
def configure_openldap_auth_mode(browser, available_auth_modes):
    """Configure LDAP authentication mode"""
    if 'miq_openldap' in available_auth_modes:
        auth_mode = current_appliance.server.authentication
        server_data = cfme_data.get('auth_modes', {})['miq_openldap']
        auth_mode.set_auth_mode(**server_data)
        yield
        current_appliance.server.login_admin()
        auth_mode.set_auth_mode()
    else:
        yield


@pytest.yield_fixture(scope='module')
def configure_openldap_auth_mode_default_groups(browser, available_auth_modes):
    """Configure LDAP authentication mode"""
    if 'miq_openldap' in available_auth_modes:
        auth_mode = current_appliance.server.authentication
        server_data = cfme_data.get('auth_modes', {})['miq_openldap']
        server_data['get_groups'] = False
        server_data['default_groups'] = 'EvmRole-user'
        auth_mode.set_auth_mode(**server_data)
        yield
        current_appliance.server.login_admin()
        auth_mode.set_auth_mode()
    else:
        yield


@pytest.yield_fixture(scope='function')
def configure_aws_iam_auth_mode(appliance, available_auth_modes):
    """Configure AWS IAM authentication mode"""
    if 'miq_aws_iam' in available_auth_modes:
        auth_mode = appliance.server.authentication
        fill_data = cfme_data.auth_modes.miq_aws_iam.copy()
        creds = credentials[fill_data.pop('credentials')]  # remove cred key from fill_data with pop
        fill_data.update(
            {'access_key': creds['username'],
             'secret_key': creds['password']})
        auth_mode.set_auth_mode(**fill_data)
        yield
        current_appliance.server.login_admin()
        auth_mode.set_auth_mode()
    else:
        # Need this configuration data to test, can't make up aws_iam account.
        pytest.skip('miq_aws_iam yaml configuration not available for configure_aws_iam_auth_mode')


# TODO remove this fixture, its doing what the above fixtures are doing but taking an argument
@pytest.fixture()
def configure_auth(request, auth_mode):
    data = cfme_data['auth_modes'].get(auth_mode, {})
    auth_settings = current_appliance.server.authentication
    if auth_mode == 'ext_ipa':
        request.addfinalizer(disable_external_auth_ipa)
        setup_external_auth_ipa(**data)
    elif auth_mode == 'ext_openldap':
        request.addfinalizer(disable_external_auth_openldap)
        setup_external_auth_openldap(**data)
    elif auth_mode in ['miq_openldap', 'miq_ldap']:
        auth_settings.set_auth_mode(**data)
        request.addfinalizer(current_appliance.server.login_admin)
        request.addfinalizer(auth_settings.set_auth_mode())
    elif auth_mode == 'miq_aws_iam':
        aws_iam_creds = credentials[data.pop('credentials')]
        data['access_key'] = aws_iam_creds['username']
        data['secret_key'] = aws_iam_creds['password']
        auth_settings.set_auth_mode(**data)
        request.addfinalizer(current_appliance.server.login_admin)
        request.addfinalizer(auth_settings.set_auth_mode())
    else:
        pytest.skip("auth_mode specified is not a expected value for cfme_auth tests")
