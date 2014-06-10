# -*- coding: utf-8 -*-
import uuid

import pytest

import cfme.web_ui.flash as flash
import utils.error as error
from cfme.infrastructure import provider
from utils import testgen
from utils.randomness import generate_random_string
from utils.update import update

pytest_generate_tests = testgen.generate(testgen.infra_providers, scope="module")


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


@pytest.mark.usefixtures('has_no_infra_providers')
def test_providers_discovery(provider_crud):
    provider.discover_from_provider(provider_crud)
    flash.assert_message_match('Infrastructure Providers: Discovery successfully initiated')
    provider.wait_for_a_provider()


@pytest.mark.smoke
@pytest.mark.usefixtures('has_no_infra_providers')
def test_provider_add(provider_crud):
    """ Tests that a provider can be added """
    provider_crud.create()
    flash.assert_message_match('Infrastructure Providers "%s" was saved' % provider_crud.name)
    # Fails on upstream, vsphere55 - BZ1087476
    provider_crud.validate()


@pytest.mark.usefixtures('has_no_infra_providers')
def test_provider_add_with_bad_credentials(provider_crud):
    provider_crud.credentials = provider.get_credentials_from_config('bad_credentials')
    if isinstance(provider_crud, provider.VMwareProvider):
        with error.expected('Cannot complete login due to an incorrect user name or password.'):
            provider_crud.create(validate_credentials=True)
    elif isinstance(provider_crud, provider.RHEVMProvider):
        with error.expected('401 Unauthorized'):
            provider_crud.create(validate_credentials=True)


@pytest.mark.usefixtures('has_no_infra_providers')
def test_provider_edit(provider_crud):
    """ Tests that editing a management system shows the proper detail after an edit."""
    provider_crud.create()
    old_name = provider_crud.name
    with update(provider_crud):
        provider_crud.name = str(uuid.uuid4())  # random uuid
    flash.assert_message_match('Infrastructure Provider "%s" was saved' % provider_crud.name)

    with update(provider_crud):
        provider_crud.name = old_name  # old name
    flash.assert_message_match('Infrastructure Provider "%s" was saved' % provider_crud.name)


def test_provider_delete(provider_crud):
    provider_crud.delete(cancel=False)
    flash.assert_message_match(
        'Delete initiated for 1 Infrastructure Provider from the CFME Database')
    provider.wait_for_provider_delete(provider_crud)
