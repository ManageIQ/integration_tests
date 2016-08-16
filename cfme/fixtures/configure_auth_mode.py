from __future__ import unicode_literals
import pytest
from utils.conf import cfme_data, credentials
from utils.ext_auth import disable_external_auth_ipa, setup_external_auth_ipa
from cfme.configure import configuration
from cfme.login import login_admin


@pytest.fixture(scope='session')
def available_auth_modes():
    return cfme_data.get('auth_modes', {}).keys()


@pytest.yield_fixture(scope='module')
def configure_ldap_auth_mode(browser, available_auth_modes):
    """Configure LDAP authentication mode"""
    if 'ldap' in available_auth_modes:
        server_data = cfme_data.get('auth_modes', {})['ldap']
        configuration.set_auth_mode(**server_data)
        yield
        login_admin()
        configuration.set_auth_mode(mode='database')
    else:
        yield


@pytest.yield_fixture(scope='module')
def configure_openldap_auth_mode(browser, available_auth_modes):
    """Configure LDAP authentication mode"""
    if 'openldap' in available_auth_modes:
        server_data = cfme_data.get('auth_modes', {})['openldap']
        configuration.set_auth_mode(**server_data)
        yield
        login_admin()
        configuration.set_auth_mode(mode='database')
    else:
        yield


@pytest.yield_fixture(scope='module')
def configure_openldap_auth_mode_default_groups(browser, available_auth_modes):
    """Configure LDAP authentication mode"""
    if 'openldap' in available_auth_modes:
        server_data = cfme_data.get('auth_modes', {})['openldap']
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
    if 'aws_iam' in available_auth_modes:
        aws_iam_data = dict(cfme_data.get('auth_modes', {})['aws_iam'])
        aws_iam_creds = credentials[aws_iam_data.pop('credentials')]
        aws_iam_data['access_key'] = aws_iam_creds['username']
        aws_iam_data['secret_key'] = aws_iam_creds['password']
        configuration.set_auth_mode(**aws_iam_data)
        yield
        login_admin()
        configuration.set_auth_mode(mode='database')
    else:
        yield


def _configure_external_auth_ipa(request):
    if "ipa" not in cfme_data:
        pytest.skip("No IPA server in configuration!")
    data = cfme_data.get("ipa", {})
    request.addfinalizer(disable_external_auth_ipa)
    setup_external_auth_ipa(**data)


@pytest.fixture(scope="function")
def configure_external_auth_ipa(request):
    _configure_external_auth_ipa(request)


@pytest.fixture(scope="module")
def configure_external_auth_ipa_module(request):
    _configure_external_auth_ipa(request)


@pytest.fixture(scope="class")
def configure_external_auth_ipa_class(request):
    _configure_external_auth_ipa(request)
