import pytest
from time import sleep

import cfme.utils.auth as authutil
from cfme.utils.log import logger


@pytest.fixture(scope='module')
def amazon_auth_provider():
    try:
        return authutil.get_auth_crud('amazon')
    except KeyError:
        pytest.skip('amazon auth provider not found in auth_data.auth_providers, skipping test.')


@pytest.fixture(scope='module')
def setup_aws_auth_provider(appliance, amazon_auth_provider):
    """Configure AWS IAM authentication mode"""
    original_config = appliance.server.authentication.auth_settings
    appliance.server.authentication.configure(auth_mode='amazon',
                                              auth_provider=amazon_auth_provider)
    yield

    appliance.server.authentication.auth_settings = original_config
    appliance.server.login_admin()
    appliance.server.authentication.configure(auth_mode='database')


@pytest.fixture(scope='function')
def auth_provider(prov_key):
    return authutil.get_auth_crud(prov_key)


@pytest.fixture(scope='function')
def auth_user_data(auth_provider, user_type):
    """Grab user data attrdict from auth provider's user data in yaml

    Expected formatting of yaml containing user data:

    test_users:
    -
      username: ldapuser2
      password: mysecretpassworddontguess
      fullname: Ldap User2
      groups:
        - customgroup1
      providers:
        - freeipa01
      user_types:
        - uid

        Only include user data for users where the user_type matches that under test

        Assert the data isn't empty, and skip the test if so

    """
    try:
        data = [user
                for user in auth_provider.user_data
                if user_type in user.user_types]
        assert data
    except (KeyError, AttributeError, AssertionError):
        logger.exception('Exception fetching auth_user_data from yaml')
        pytest.skip('No yaml data for auth_prov {} under "auth_data.test_data"'
                    .format(auth_provider))
    return data


@pytest.fixture(scope='session')
def ensure_resolvable_hostname(appliance):
    """
    Intended for use with freeipa configuration, ensures a resolvable hostname on the appliance

    Tries to resolve the appliance hostname property and skips the test if it can't
    """
    appliance.set_resolvable_hostname()


@pytest.fixture(scope='function')
def configure_auth(appliance, auth_mode, auth_provider, user_type, ensure_resolvable_hostname,
                   request):
    """Given auth_mode, auth_provider, user_type parametrization, configure auth for login
    testing.

    Saves original auth settings
    Configures external or internal auth modes
    Separate freeipa / openldap config methods and finalizers
    Restores original auth settings after yielding
    """
    original_config = appliance.server.authentication.auth_settings
    logger.debug('Original auth settings before configure_auth fixture: %r', original_config)
    if auth_mode.lower() != 'external':
        appliance.server.authentication.configure(auth_mode=auth_mode,
                                                  auth_provider=auth_provider,
                                                  user_type=user_type)
    elif auth_mode.lower() == 'external':  # extra explicit
        if auth_provider.auth_type == 'freeipa':
            appliance.configure_freeipa(auth_provider)
            request.addfinalizer(appliance.disable_freeipa)
        elif auth_provider.auth_type == 'openldaps':
            appliance.configure_openldap(auth_provider)
            request.addfinalizer(appliance.disable_openldap)

    # Auth reconfigure is super buggy and sensitive to timing
    # Just waiting on sssd to be running, or an httpd restart isn't sufficient
    sleep(30)
    yield
    # return to original auth config
    appliance.server.authentication.auth_settings = original_config
    appliance.httpd.restart()
    appliance.wait_for_web_ui()
