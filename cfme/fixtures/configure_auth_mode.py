import pytest

from cfme.utils.conf import credentials, auth_data
from cfme.utils.appliance import current_appliance
from cfme.utils.ext_auth import (disable_external_auth_ipa, disable_external_auth_openldap,
    setup_external_auth_ipa, setup_external_auth_openldap)


def get_auth_settings(appliance):
    """Grab the authentication settings from the UI form, popping the title widget content out"""
    settings = {}
    settings['auth_mode'] = appliance.server.authentication.auth_mode
    settings['auth_settings'] = appliance.server.authentication.auth_settings
    settings['auth_settings'].pop('title')
    return settings


@pytest.fixture(scope='session')
def available_auth_modes():
    return auth_data.get('auth_providers', {}).keys()


@pytest.yield_fixture(scope='module')
def configure_ldap_auth_mode(browser, available_auth_modes):
    """Configure LDAP authentication mode"""
    if 'miq_ldap' in available_auth_modes:
        auth_mode = current_appliance.server.authentication
        server_data = auth_data.get('auth_providers', {}).get('miq_ldap')
        auth_mode.configure_auth(**server_data)
        yield
        current_appliance.server.login_admin()
        auth_mode.configure_auth()
    else:
        yield


@pytest.yield_fixture(scope='module')
def configure_openldap_auth_mode(browser, available_auth_modes):
    """Configure LDAP authentication mode"""
    if 'miq_openldap' in available_auth_modes:
        auth_mode = current_appliance.server.authentication
        server_data = auth_data.get('auth_providers', {}).get('miq_openldap')
        auth_mode.configure_auth(**server_data)
        yield
        current_appliance.server.login_admin()
        auth_mode.configure_auth()
    else:
        yield


@pytest.yield_fixture(scope='module')
def configure_openldap_auth_mode_default_groups(browser, available_auth_modes):
    """Configure LDAP authentication mode"""
    if 'miq_openldap' in available_auth_modes:
        auth_mode = current_appliance.server.authentication
        server_data = auth_data.get('auth_providers', {}).get('miq_openldap')
        server_data['get_groups'] = False
        server_data['default_groups'] = 'EvmRole-user'
        auth_mode.configure_auth(**server_data)
        yield
        current_appliance.server.login_admin()
        auth_mode.configure_auth()
    else:
        yield


@pytest.yield_fixture(scope='module')
def configure_aws_iam_auth_mode(appliance, available_auth_modes):
    """Configure AWS IAM authentication mode"""
    if 'miq_aws' in available_auth_modes:
        # TODO use new get_auth_settings function to store original settings
        auth_settings = appliance.server.authentication
        orig_mode = auth_settings.auth_mode
        orig_settings = auth_settings.auth_settings
        orig_settings.pop('title')
        yaml_data = auth_data.get('auth_providers', {}).get('miq_aws', {}).copy()
        creds = credentials[yaml_data.pop('credentials')]  # remove cred key from fill_data with pop
        fill_data = {
            'access_key': creds['username'],
            'secret_key': creds['password'],
            'get_groups': yaml_data.get('get_groups', False)}

        auth_settings.configure_auth(auth_mode='Amazon', **fill_data)
        auth_settings.set_session_timeout(hours=yaml_data.get('timeout_h', '24'),
                                          minutes=yaml_data.get('timeout_m', '0'))
        yield
        current_appliance.server.login_admin()
        auth_settings.configure_auth(auth_mode=orig_mode, **orig_settings)
        auth_settings.set_session_timeout(hours=orig_settings.get('hours_timeout', '24'),
                                          minutes=orig_settings.get('minutes_timeout', '0'))
    else:
        # Need this configuration data to test, can't make up aws_iam account.
        pytest.skip('miq_aws yaml configuration not available for configure_aws_iam_auth_mode')


# TODO remove this fixture, its doing what the above fixtures are doing but taking an argument
@pytest.fixture()
def configure_auth(appliance, request, auth_mode):
    data = auth_data['auth_providers'].get(auth_mode, {})
    app_auth = appliance.server.authentication
    if auth_mode == 'ext_ipa':
        request.addfinalizer(disable_external_auth_ipa)
        setup_external_auth_ipa(**data)
    elif auth_mode == 'ext_openldap':
        request.addfinalizer(disable_external_auth_openldap)
        setup_external_auth_openldap(appliance, **data)
    elif auth_mode in ['miq_openldap', 'miq_ldap']:
        app_auth.configure_auth(**data)
        request.addfinalizer(current_appliance.server.login_admin)
        request.addfinalizer(app_auth.configure_auth)
    elif auth_mode == 'miq_aws':
        aws_iam_creds = credentials[data.pop('credentials')]
        data['access_key'] = aws_iam_creds['username']
        data['secret_key'] = aws_iam_creds['password']
        app_auth.configure_auth(**data)
        request.addfinalizer(current_appliance.server.login_admin)
        request.addfinalizer(app_auth.configure_auth)
    else:
        pytest.skip("auth_mode specified is not a expected value for cfme_auth tests")
