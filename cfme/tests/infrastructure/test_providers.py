# -*- coding: utf-8 -*-
import fauxfactory
import uuid

import pytest

import cfme.web_ui.flash as flash
import utils.error as error
from cfme.infrastructure import provider
from utils import testgen, providers, version
from utils.update import update


pytest_generate_tests = testgen.generate(testgen.infra_providers, scope="function")


@pytest.mark.sauce
def test_empty_discovery_form_validation():
    """ Tests that the flash message is correct when discovery form is empty."""
    provider.discover(None)
    flash.assert_message_match('At least 1 item must be selected for discovery')


@pytest.mark.sauce
def test_discovery_cancelled_validation():
    """ Tests that the flash message is correct when discovery is cancelled."""
    provider.discover(None, cancel=True)
    flash.assert_message_match('Infrastructure Providers Discovery was cancelled by the user')


@pytest.mark.sauce
def test_add_cancelled_validation():
    """Tests that the flash message is correct when add is cancelled."""
    prov = provider.VMwareProvider()
    prov.create(cancel=True)
    flash.assert_message_match('Add of new Infrastructure Provider was cancelled by the user')


@pytest.mark.sauce
def test_type_required_validation():
    """Test to validate type while adding a provider"""
    prov = provider.Provider()
    with error.expected('Type is required'):
        prov.create()


def test_name_required_validation():
    """Tests to validate the name while adding a provider"""
    prov = provider.VMwareProvider(
        name=None,
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address='10.10.10.10')

    with error.expected("Name can't be blank"):
        prov.create()


def test_host_name_required_validation():
    """Test to validate the hostname while adding a provider"""
    prov = provider.VMwareProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=None,
        ip_address='10.10.10.11')

    with error.expected("Host Name can't be blank"):
        prov.create()


@pytest.mark.meta(blockers=[1209756])
@pytest.mark.uncollectif(lambda: version.current_version() > "5.4.0.0.24")
def test_ip_required_validation():
    """Test to validate the ip address while adding a provider"""
    prov = provider.VMwareProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address=None)

    with error.expected("IP Address can't be blank"):
        prov.create()


@pytest.mark.xfail(message='http://cfme-tests.readthedocs.org/guides/gotchas.html#'
    'selenium-is-not-clicking-on-the-element-it-says-it-is')
def test_name_max_character_validation():
    """Test to validate max character for name field"""
    prov = provider.VMwareProvider(
        name=fauxfactory.gen_alphanumeric(256),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address='10.10.10.12')
    prov.create()
    prov.delete(cancel=False)


def test_host_name_max_character_validation():
    """Test to validate max character for host name field"""
    prov = provider.VMwareProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(256),
        ip_address='10.10.10.13')
    prov.create()
    prov.delete(cancel=False)


def test_ip_max_character_validation():
    """Test to validate max character for ip address field"""
    prov = provider.VMwareProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address='10.10.10.14')
    prov.create()
    prov.delete(cancel=False)


def test_api_port_max_character_validation():
    """Test to validate max character for api port field"""
    prov = provider.RHEVMProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address='10.10.10.15',
        api_port=fauxfactory.gen_alphanumeric(15))
    prov.create()
    prov.delete(cancel=False)


@pytest.mark.usefixtures('has_no_infra_providers')
def test_providers_discovery(request, provider_crud):
    """Tests provider discovery

    Metadata:
        test_flag: crud
    """
    provider.discover_from_provider(provider_crud)
    flash.assert_message_match('Infrastructure Providers: Discovery successfully initiated')
    request.addfinalizer(providers.clear_infra_providers)
    provider.wait_for_a_provider()


@pytest.mark.usefixtures('has_no_infra_providers')
def test_provider_add_with_bad_credentials(provider_crud):
    """Tests provider add with bad credentials

    Metadata:
        test_flag: crud
    """
    provider_crud.credentials = provider.get_credentials_from_config('bad_credentials')
    if isinstance(provider_crud, provider.VMwareProvider):
        with error.expected('Cannot complete login due to an incorrect user name or password.'):
            provider_crud.create(validate_credentials=True)
    elif isinstance(provider_crud, provider.RHEVMProvider):
        with error.expected('401 Unauthorized'):
            provider_crud.create(validate_credentials=True)


@pytest.mark.usefixtures('has_no_infra_providers')
def test_provider_crud(provider_crud):
    """Tests provider add with good credentials

    Metadata:
        test_flag: crud
    """
    provider_crud.create()
    # Fails on upstream, all provider types - BZ1087476
    provider_crud.validate(db=False)

    old_name = provider_crud.name
    with update(provider_crud):
        provider_crud.name = str(uuid.uuid4())  # random uuid

    with update(provider_crud):
        provider_crud.name = old_name  # old name

    provider_crud.delete(cancel=False)
    provider.wait_for_provider_delete(provider_crud)
