# -*- coding: utf-8 -*-
import fauxfactory
import uuid

import pytest

import cfme.web_ui.flash as flash
import utils.error as error
from cfme.infrastructure.provider import (discover, Provider, VMwareProvider, RHEVMProvider,
    wait_for_a_provider)
from cfme.fixtures import pytest_selenium as sel
from utils import testgen, providers, version
from utils.providers import get_credentials_from_config
from utils.update import update


pytest_generate_tests = testgen.generate(testgen.infra_providers, scope="function")

MANAGE_INFRA_PROVIDER = [
    ['Everything', 'Infrastructure', 'Providers'],
    ['Everything', 'Infrastructure', 'Providers', 'Create'],
    ['Everything', 'Infrastructure', 'Providers', 'Modify'],
    ['Everything', 'Infrastructure', 'Providers', 'View'],
]

MANAGE_CLOUD_PROVIDER = [
    ['Everything', 'Infrastructure', 'Providers'],
    ['Everything', 'Infrastructure', 'Providers', 'Create'],
    ['Everything', 'Infrastructure', 'Providers', 'Modify'],
    ['Everything', 'Infrastructure', 'Providers', 'View'],  # <------ infra_view
]


@pytest.mark.posneg([['Everything', 'Infrastructure', 'Providers']])
def test_navigate_infra():
    sel.force_navigate('infrastructure_providers')


@pytest.mark.posneg([MANAGE_INFRA_PROVIDER, MANAGE_CLOUD_PROVIDER])
@pytest.mark.sauce
def test_empty_discovery_form_validation():
    """ Tests that the flash message is correct when discovery form is empty."""
    discover(None)
    flash.assert_message_match('At least 1 item must be selected for discovery')


@pytest.mark.sauce
def test_discovery_cancelled_validation():
    """ Tests that the flash message is correct when discovery is cancelled."""
    discover(None, cancel=True)
    flash.assert_message_match('Infrastructure Providers Discovery was cancelled by the user')


@pytest.mark.sauce
def test_add_cancelled_validation():
    """Tests that the flash message is correct when add is cancelled."""
    prov = VMwareProvider()
    prov.create(cancel=True)
    flash.assert_message_match('Add of new Infrastructure Provider was cancelled by the user')


@pytest.mark.sauce
def test_type_required_validation():
    """Test to validate type while adding a provider"""
    prov = Provider()
    with error.expected('Type is required'):
        prov.create()


def test_name_required_validation():
    """Tests to validate the name while adding a provider"""
    prov = VMwareProvider(
        name=None,
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address='10.10.10.10')

    with error.expected("Name can't be blank"):
        prov.create()


def test_host_name_required_validation():
    """Test to validate the hostname while adding a provider"""
    prov = VMwareProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=None,
        ip_address='10.10.10.11')

    with error.expected("Host Name can't be blank"):
        prov.create()


@pytest.mark.meta(blockers=[1209756])
@pytest.mark.uncollectif(lambda: version.current_version() > "5.4.0.0.24")
def test_ip_required_validation():
    """Test to validate the ip address while adding a provider"""
    prov = VMwareProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address=None)

    with error.expected("IP Address can't be blank"):
        prov.create()


@pytest.mark.xfail(message='http://cfme-tests.readthedocs.org/guides/gotchas.html#'
    'selenium-is-not-clicking-on-the-element-it-says-it-is')
def test_name_max_character_validation():
    """Test to validate max character for name field"""
    prov = VMwareProvider(
        name=fauxfactory.gen_alphanumeric(256),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address='10.10.10.12')
    prov.create()
    prov.delete(cancel=False)


def test_host_name_max_character_validation():
    """Test to validate max character for host name field"""
    prov = VMwareProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(256),
        ip_address='10.10.10.13')
    prov.create()
    prov.delete(cancel=False)


def test_ip_max_character_validation():
    """Test to validate max character for ip address field"""
    prov = VMwareProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address='10.10.10.14')
    prov.create()
    prov.delete(cancel=False)


def test_api_port_max_character_validation():
    """Test to validate max character for api port field"""
    prov = RHEVMProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address='10.10.10.15',
        api_port=fauxfactory.gen_alphanumeric(15))
    prov.create()
    prov.delete(cancel=False)


@pytest.mark.usefixtures('has_no_infra_providers')
def test_providers_discovery(request, provider):
    """Tests provider discovery

    Metadata:
        test_flag: crud
    """
    provider.discover()
    flash.assert_message_match('Infrastructure Providers: Discovery successfully initiated')
    request.addfinalizer(providers.clear_infra_providers)
    wait_for_a_provider()


@pytest.mark.usefixtures('has_no_infra_providers')
def test_provider_add_with_bad_credentials(provider):
    """Tests provider add with bad credentials

    Metadata:
        test_flag: crud
    """
    provider.credentials['default'] = get_credentials_from_config('bad_credentials')
    if isinstance(provider, VMwareProvider):
        with error.expected('Cannot complete login due to an incorrect user name or password.'):
            provider.create(validate_credentials=True)
    elif isinstance(provider, RHEVMProvider):
        error_message = version.pick(
            {'5.4': '401 Unauthorized',
             '5.5': 'Credential validation was not successful: '
                'Login failed due to a bad username or password.'}
        )
        with error.expected(error_message):
            provider.create(validate_credentials=True)


@pytest.mark.usefixtures('has_no_infra_providers')
def test_provider_crud(provider):
    """Tests provider add with good credentials

    Metadata:
        test_flag: crud
    """
    provider.create()
    # Fails on upstream, all provider types - BZ1087476
    provider.validate_stats(ui=True)

    old_name = provider.name
    with update(provider):
        provider.name = str(uuid.uuid4())  # random uuid

    with update(provider):
        provider.name = old_name  # old name

    provider.delete(cancel=False)
    provider.wait_for_delete()
