# -*- coding: utf-8 -*-
import uuid

import pytest

import cfme.web_ui.flash as flash
import utils.error as error
from cfme.infrastructure import provider
from utils import testgen
from utils import providers
from utils.randomness import generate_random_string
from utils.update import update

pytest_generate_tests = testgen.generate(testgen.infra_providers, scope="module")

# To avoid issues with deleting and re-adding provider, this bugzilla is targeted at that problem
# We create shortcut for it here, so we can then simply mark the tests that use
# 'has_no_infra_providers' fixture.
bz1087476 = pytest.mark.bugzilla(
    1087476, unskip={1087476: lambda appliance_version: appliance_version < "5.3"})


def test_empty_discovery_form_validation():
    """ Tests that the flash message is correct when discovery form is empty."""
    provider.discover(None)
    flash.assert_message_match('At least 1 item must be selected for discovery')


def test_discovery_cancelled_validation():
    """ Tests that the flash message is correct when discovery is cancelled."""
    provider.discover(None, cancel=True)
    flash.assert_message_match('Infrastructure Providers Discovery was cancelled by the user')


def test_add_cancelled_validation():
    """Tests that the flash message is correct when add is cancelled."""
    prov = provider.VMwareProvider()
    prov.create(cancel=True)
    flash.assert_message_match('Add of new Infrastructure Provider was cancelled by the user')


def test_type_required_validation():
    """Test to validate type while adding a provider"""
    prov = provider.Provider()
    with error.expected('Type is required'):
        prov.create()


def test_name_required_validation():
    """Tests to validate the name while adding a provider"""
    prov = provider.VMwareProvider(
        name=None,
        hostname=generate_random_string(size=5),
        ip_address='10.10.10.10')

    with error.expected("Name can't be blank"):
        prov.create()


def test_host_name_required_validation():
    """Test to validate the hostname while adding a provider"""
    prov = provider.VMwareProvider(
        name=generate_random_string(size=5),
        hostname=None,
        ip_address='10.10.10.10')

    with error.expected("Host Name can't be blank"):
        prov.create()


def test_ip_required_validation():
    """Test to validate the ip address while adding a provider"""
    prov = provider.VMwareProvider(
        name=generate_random_string(size=5),
        hostname=generate_random_string(size=5),
        ip_address=None)

    with error.expected("IP Address can't be blank"):
        prov.create()


@pytest.mark.xfail(message='http://cfme-tests.readthedocs.org/guides/gotchas.html#'
    'selenium-is-not-clicking-on-the-element-it-says-it-is')
def test_name_max_character_validation():
    """Test to validate max character for name field"""
    prov = provider.VMwareProvider(
        name=generate_random_string(size=256),
        hostname=generate_random_string(size=5),
        ip_address='10.10.10.10')
    prov.create()
    prov.delete(cancel=False)


def test_host_name_max_character_validation():
    """Test to validate max character for host name field"""
    prov = provider.VMwareProvider(
        name=generate_random_string(size=5),
        hostname=generate_random_string(size=256),
        ip_address='10.10.10.11')
    prov.create()
    prov.delete(cancel=False)


def test_ip_max_character_validation():
    """Test to validate max character for ip address field"""
    prov = provider.VMwareProvider(
        name=generate_random_string(size=5),
        hostname=generate_random_string(size=5),
        ip_address='10.10.10.12')
    prov.create()
    prov.delete(cancel=False)


def test_api_port_max_character_validation():
    """Test to validate max character for api port field"""
    prov = provider.RHEVMProvider(
        name=generate_random_string(size=5),
        hostname=generate_random_string(size=5),
        ip_address='10.10.10.13',
        api_port=generate_random_string(size=15))
    prov.create()
    prov.delete(cancel=False)


@bz1087476
@pytest.mark.usefixtures('has_no_infra_providers')
def test_providers_discovery(request, provider_crud):
    provider.discover_from_provider(provider_crud)
    flash.assert_message_match('Infrastructure Providers: Discovery successfully initiated')
    request.addfinalizer(providers.clear_infra_providers)
    provider.wait_for_a_provider()


@bz1087476
@pytest.mark.usefixtures('has_no_infra_providers')
def test_provider_add_with_bad_credentials(provider_crud):
    provider_crud.credentials = provider.get_credentials_from_config('bad_credentials')
    if isinstance(provider_crud, provider.VMwareProvider):
        with error.expected('Cannot complete login due to an incorrect user name or password.'):
            provider_crud.create(validate_credentials=True)
    elif isinstance(provider_crud, provider.RHEVMProvider):
        with error.expected('401 Unauthorized'):
            provider_crud.create(validate_credentials=True)


@bz1087476
@pytest.mark.usefixtures('has_no_infra_providers')
def test_provider_crud(provider_crud):
    """ Tests that a provider can be added """
    provider_crud.create()
    # Fails on upstream, all provider types - BZ1087476
    provider_crud.validate()

    old_name = provider_crud.name
    with update(provider_crud):
        provider_crud.name = str(uuid.uuid4())  # random uuid

    with update(provider_crud):
        provider_crud.name = old_name  # old name

    provider_crud.delete(cancel=False)
    provider.wait_for_provider_delete(provider_crud)
