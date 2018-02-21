import pytest
from time import sleep

import cfme.utils.auth as authutil
from cfme.utils.conf import auth_data
from cfme.utils.appliance import current_appliance
from cfme.utils.log import logger


def get_auth_settings(appliance):
    """Grab the authentication settings from the UI form, popping the title widget content out"""
    settings = {'auth_mode': appliance.server.authentication.auth_mode}
    settings['auth_settings'] = appliance.server.authentication.auth_settings
    settings['auth_settings'].pop('title')
    return settings


@pytest.fixture(scope='module')
def amazon_auth_provider():
    try:
        return authutil.get_auth_crud('amazon')
    except KeyError:
        pytest.skip('amazon auth provider not found in auth_data.auth_providers, skipping test.')


@pytest.fixture(scope='module')
def setup_aws_auth_provider(appliance, amazon_auth_provider):
    """Configure AWS IAM authentication mode"""
    appliance.server.authentication.configure(auth_mode='amazon',
                                              auth_provider=amazon_auth_provider)
    yield

    current_appliance.server.login_admin()
    appliance.server.authentication.configure(auth_mode='database')


@pytest.fixture(scope='function')
def auth_provider(prov_key):
        return authutil.get_auth_crud(prov_key)


@pytest.fixture(scope='function')
def auth_user_data(prov_key, user_type):
    try:
        data = [user
                for user in auth_data.test_data.test_users
                if prov_key in user.providers and user_type in user.user_types]
        assert data
    except (KeyError, AttributeError, AssertionError):
        logger.exception('Exception fetching auth_user_data from yaml')
        pytest.skip('No yaml data for auth_prov {} under "auth_data.test_data"'.format(prov_key))
    return data


@pytest.yield_fixture(scope='function')
def configure_auth(appliance, auth_mode, auth_provider, user_type, request):
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
    sleep(30)
    yield
    # return to database auth config
    appliance.server.authentication.configure(auth_mode='database')
    appliance.httpd.restart()
    appliance.wait_for_web_ui()
