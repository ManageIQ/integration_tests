import pytest

from fixtures.navigation import cnf_configuration_pg
from utils.conf import cfme_data, credentials


@pytest.yield_fixture(scope='module')  # IGNORE:E1101
def configure_ldap_auth_mode():
    """Configure LDAP authentication mode"""
    server_data = cfme_data['auth_modes']['ldap_server']
    auth_pg = cnf_configuration_pg().click_on_settings()\
        .click_on_current_server_tree_node()\
        .click_on_authentication_tab()
    if auth_pg.current_auth_mode != server_data['mode']:
        auth_pg.ldap_server_fill_data(**server_data)
        if server_data['get_groups'] and server_data['mode'] != "database":
            auth_pg.validate()
            assert "LDAP Settings validation was successful" in auth_pg.flash.message,\
                "Validate flash message did not match"
        auth_pg = auth_pg.save()
        assert "Authentication settings saved" in auth_pg.flash.message,\
            "Auth page save flash message did not match"

    yield

    auth_pg = cnf_configuration_pg().click_on_settings()\
        .click_on_current_server_tree_node()\
        .click_on_authentication_tab()
    auth_pg.current_auth_mode = 'database'
    auth_pg.save()


@pytest.yield_fixture(scope='module')  # IGNORE:E1101
def configure_aws_iam_auth_mode():
    """Configure AWS IAM authentication mode"""
    aws_iam_data = dict(cfme_data['auth_modes']['aws_iam'])
    aws_iam_creds = credentials[aws_iam_data.pop('credentials')]
    aws_iam_data['access_key'] = aws_iam_creds['username']
    aws_iam_data['secret_key'] = aws_iam_creds['password']
    auth_pg = cnf_configuration_pg().click_on_settings()\
        .click_on_current_server_tree_node()\
        .click_on_authentication_tab()
    if auth_pg.current_auth_mode != aws_iam_data['mode']:
        auth_pg.aws_iam_fill_data(**aws_iam_data)
        if aws_iam_data['mode'] != "database":
            auth_pg.validate()
            assert "Amazon Settings validation was successful" in auth_pg.flash.message,\
                "Validate flash message did not match"
        auth_pg = auth_pg.save()
        assert "Authentication settings saved" in auth_pg.flash.message,\
            "Auth page save flash message did not match"

    yield

    auth_pg = cnf_configuration_pg().click_on_settings()\
        .click_on_current_server_tree_node()\
        .click_on_authentication_tab()
    auth_pg.current_auth_mode = 'database'
    auth_pg.save()
