# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621
import uuid

import pytest

import cfme.web_ui.flash as flash
import utils.error as error
from cfme import Credential
from cfme.cloud import provider
from utils import testgen
from utils.randomness import generate_random_string
from utils.update import update

pytest_generate_tests = testgen.generate(testgen.cloud_providers, scope="module")


def test_empty_discovery_form_validation():
    """ Tests that the flash message is correct when discovery form is empty."""
    provider.discover(None)
    flash.assert_message_match('User ID is required')


def test_discovery_cancelled_validation():
    """ Tests that the flash message is correct when discovery is cancelled."""
    provider.discover(None, cancel=True)
    flash.assert_message_match('Amazon Cloud Providers Discovery was cancelled by the user')


def test_add_cancelled_validation():
    """Tests that the flash message is correct when add is cancelled."""
    prov = provider.EC2Provider()
    prov.create(cancel=True)
    flash.assert_message_match('Add of new Cloud Provider was cancelled by the user')


def test_password_mismatch_validation():
    cred = Credential(
        principal=generate_random_string(size=5),
        secret=generate_random_string(size=5),
        verify_secret=generate_random_string(size=7))

    provider.discover(cred)
    flash.assert_message_match('Password/Verify Password do not match')


@pytest.mark.usefixtures('has_no_cloud_providers')
def test_providers_discovery_amazon():
    raise pytest.skip('discovery and teardown is not parallel; this routinely times out')
    amazon_creds = provider.get_credentials_from_config('cloudqe_amazon')
    provider.discover(amazon_creds)
    flash.assert_message_match('Amazon Cloud Providers: Discovery successfully initiated')
    provider.wait_for_a_provider()


@pytest.mark.usefixtures('has_no_cloud_providers')
def test_provider_add_with_bad_credentials(provider_crud):
    provider_crud.credentials = provider.get_credentials_from_config('bad_credentials')
    with error.expected('Login failed due to a bad username or password.'):
        provider_crud.create(validate_credentials=True)


@pytest.mark.smoke
@pytest.mark.usefixtures('has_no_cloud_providers')
def test_provider_crud(provider_crud):
    """ Tests that a provider can be added """
    provider_crud.create()
    provider_crud.validate()

    old_name = provider_crud.name
    with update(provider_crud):
        provider_crud.name = str(uuid.uuid4())  # random uuid

    with update(provider_crud):
        provider_crud.name = old_name  # old name

    provider_crud.delete(cancel=False)
    provider.wait_for_provider_delete(provider_crud)


def test_type_required_validation():
    """Test to validate type while adding a provider"""
    prov = provider.Provider()

    with error.expected('Type is required'):
        prov.create()


def test_name_required_validation():
    """Tests to validate the name while adding a provider"""
    prov = provider.EC2Provider(
        name=None,
        region='us-east-1')

    with error.expected("Name can't be blank"):
        prov.create()


def test_region_required_validation():
    """Tests to validate the region while adding a provider"""
    prov = provider.EC2Provider(
        name=generate_random_string(size=5),
        region=None)

    with error.expected('Region is not included in the list'):
        prov.create()


def test_host_name_required_validation():
    """Test to validate the hostname while adding a provider"""
    prov = provider.OpenStackProvider(
        name=generate_random_string(size=5),
        hostname=None,
        ip_address='10.10.10.10')

    with error.expected("Host Name can't be blank"):
        prov.create()


def test_ip_address_required_validation():
    """Test to validate the ip address while adding a provider"""
    prov = provider.OpenStackProvider(
        name=generate_random_string(size=5),
        hostname=generate_random_string(size=5),
        ip_address=None)

    with error.expected("IP Address can't be blank"):
        prov.create()


def test_api_port_blank_validation():
    """Test to validate blank api port while adding a provider"""
    prov = provider.OpenStackProvider(
        name=generate_random_string(size=5),
        hostname=generate_random_string(size=5),
        ip_address='10.10.10.10',
        api_port='')

    prov.create()
    prov.delete(cancel=False)


def test_user_id_max_character_validation():
    cred = Credential(principal=generate_random_string(size=51))
    provider.discover(cred)


def test_password_max_character_validation():
    password = generate_random_string(size=51)
    cred = Credential(
        principal=generate_random_string(size=5),
        secret=password,
        verify_secret=password)
    provider.discover(cred)


def test_name_max_character_validation():
    """Test to validate max character for name field"""
    prov = provider.EC2Provider(
        name=generate_random_string(size=255),
        region='us-east-1')

    prov.create()
    prov.delete(cancel=False)


def test_hostname_max_character_validation():
    """Test to validate max character for hostname field"""
    prov = provider.OpenStackProvider(
        name=generate_random_string(size=5),
        hostname=generate_random_string(size=255),
        ip_address='10.10.10.10')

    prov.create()
    prov.delete(cancel=False)


def test_ip_max_valid_character_validation():
    """Test to validate max character for ip address field with valid ip address"""
    prov = provider.OpenStackProvider(
        name=generate_random_string(size=5),
        hostname=generate_random_string(size=5),
        ip_address='255.255.255.254')

    prov.create()
    prov.delete(cancel=False)


def test_ip_max_invalid_character_validation():
    """Test to validate max character for ip address field using random string"""
    prov = provider.OpenStackProvider(
        name=generate_random_string(size=5),
        hostname=generate_random_string(size=5),
        ip_address=generate_random_string(size=15))

    prov.create()
    prov.delete(cancel=False)


def test_api_port_max_character_validation():
    """Test to validate max character for api port field"""
    prov = provider.OpenStackProvider(
        name=generate_random_string(size=5),
        hostname=generate_random_string(size=5),
        ip_address='10.10.10.10',
        api_port=generate_random_string(size=15))

    prov.create()
    prov.delete(cancel=False)
