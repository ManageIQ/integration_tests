from time import sleep

import pytest

import cfme.utils.auth as authutil
from cfme.utils.log import logger


@pytest.fixture(scope='module')
def amazon_auth_provider():
    try:
        return authutil.get_auth_crud('amazon')
    except KeyError:
        pytest.skip('amazon auth provider not found in auth_data.auth_providers, skipping test.')


@pytest.fixture(scope='function')
def ipa_auth_provider():
    try:
        return authutil.get_auth_crud('freeipa01')
    except KeyError:
        pytest.skip('ipa auth provider not found in auth_data.auth_providers, skipping test.')


@pytest.fixture(scope='function')
def setup_ipa_auth_provider(temp_appliance_preconfig_long, ipa_auth_provider):
    """Add/Remove IPA auth provider"""
    original_config = temp_appliance_preconfig_long.server.authentication.auth_settings
    temp_appliance_preconfig_long.server.authentication.configure(auth_mode='external',
                                              auth_provider=ipa_auth_provider)
    yield

    temp_appliance_preconfig_long.server.authentication.auth_settings = original_config
    temp_appliance_preconfig_long.server.login_admin()
    temp_appliance_preconfig_long.server.authentication.configure(auth_mode='database')


@pytest.fixture(scope='function')
def ldap_auth_provider():
    try:
        return authutil.get_auth_crud('ad_bos')
    except KeyError:
        pytest.skip(
            'ldap auth provider ad_bos not found in auth_data.auth_providers, skipping test'
        )


@pytest.fixture(scope='function')
def setup_ldap_auth_provider(appliance, ldap_auth_provider):
    """ Add/remove ldap auth provider"""
    original_config = appliance.server.authentication.auth_settings
    appliance.server.authentication.configure(auth_mode='ldap',
                                              auth_provider=ldap_auth_provider,
                                              user_type='upn')
    yield ldap_auth_provider
    appliance.server.authentication.auth_settings = original_config
    appliance.server.login_admin()
    appliance.server.authentication.configure(auth_mode='database')


@pytest.fixture(scope='module')
def setup_aws_auth_provider(temp_appliance_preconfig_long, amazon_auth_provider):
    """Configure AWS IAM authentication mode"""
    original_config = temp_appliance_preconfig_long.server.authentication.auth_settings
    temp_appliance_preconfig_long.server.authentication.configure(auth_mode='amazon',
                                              auth_provider=amazon_auth_provider)
    sleep(60)  # wait for MIQ to update, no trigger to look for, but if you try too soon it fails
    yield

    temp_appliance_preconfig_long.server.authentication.auth_settings = original_config
    temp_appliance_preconfig_long.server.login_admin()
    temp_appliance_preconfig_long.server.authentication.configure(auth_mode='database')


@pytest.fixture(scope='function')
def auth_provider(prov_key):
    return authutil.get_auth_crud(prov_key)


@pytest.fixture(scope='module')
def ensure_resolvable_hostname(temp_appliance_preconfig_long):
    """
    Intended for use with freeipa configuration, ensures a resolvable hostname on the appliance

    Tries to resolve the appliance hostname property and skips the test if it can't
    """
    assert temp_appliance_preconfig_long.set_resolvable_hostname()


@pytest.fixture(scope='function')
def configure_auth(
    temp_appliance_preconfig_long,
    auth_mode, auth_provider, user_type, request, fix_missing_hostname
):
    """Given auth_mode, auth_provider, user_type parametrization, configure auth for login
    testing.

    Saves original auth settings
    Configures external or internal auth modes
    Separate freeipa / openldap config methods and finalizers
    Restores original auth settings after yielding
    """
    original_config = temp_appliance_preconfig_long.server.authentication.auth_settings
    logger.debug('Original auth settings before configure_auth fixture: %r', original_config)
    if auth_mode.lower() != 'external':
        temp_appliance_preconfig_long.server.authentication.configure(auth_mode=auth_mode,
                                                  auth_provider=auth_provider,
                                                  user_type=user_type)
    elif auth_mode.lower() == 'external':  # extra explicit
        if auth_provider.auth_type == 'freeipa':
            temp_appliance_preconfig_long.configure_freeipa(auth_provider)
            request.addfinalizer(temp_appliance_preconfig_long.disable_freeipa)
        elif auth_provider.auth_type == 'openldaps':
            temp_appliance_preconfig_long.configure_openldap(auth_provider)
            request.addfinalizer(temp_appliance_preconfig_long.disable_openldap)

    # Auth reconfigure is super buggy and sensitive to timing
    # Just waiting on sssd to be running, or an httpd restart isn't sufficient
    sleep(30)
    yield
    # return to original auth config
    temp_appliance_preconfig_long.server.authentication.auth_settings = original_config
    temp_appliance_preconfig_long.evmserverd.restart()
    temp_appliance_preconfig_long.wait_for_web_ui()
    # After evmserverd restart, we need to logout from the appliance in the UI.
    # Otherwise the UI would be in a bad state and produce errors while testing.
    temp_appliance_preconfig_long.server.logout()
