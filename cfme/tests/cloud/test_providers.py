# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621
import fauxfactory
import uuid

import pytest

import utils.error as error
from cfme import Credential
from cfme.exceptions import FlashMessageException
from cfme.cloud.provider import (discover, EC2Provider, wait_for_a_provider,
    Provider, OpenStackProvider, properties_form)
from cfme.web_ui import fill, flash
from utils import testgen, version
from utils.providers import get_credentials_from_config
from utils.update import update

pytest_generate_tests = testgen.generate(testgen.cloud_providers, scope="function")


def test_empty_discovery_form_validation():
    """ Tests that the flash message is correct when discovery form is empty."""
    discover(None)
    ident = version.pick({version.LOWEST: 'User ID',
                          '5.4': 'Username'})
    flash.assert_message_match('{} is required'.format(ident))


def test_discovery_cancelled_validation():
    """ Tests that the flash message is correct when discovery is cancelled."""
    discover(None, cancel=True)
    flash.assert_message_match('Amazon Cloud Providers Discovery was cancelled by the user')


def test_add_cancelled_validation(request):
    """Tests that the flash message is correct when add is cancelled."""
    prov = EC2Provider()
    request.addfinalizer(prov.delete_if_exists)
    prov.create(cancel=True)
    flash.assert_message_match({
        version.LOWEST: 'Add of new Cloud Provider was cancelled by the user',
        '5.5': 'Add of Cloud Provider was cancelled by the user'})


def test_password_mismatch_validation():
    cred = Credential(
        principal=fauxfactory.gen_alphanumeric(5),
        secret=fauxfactory.gen_alphanumeric(5),
        verify_secret=fauxfactory.gen_alphanumeric(7))

    discover(cred)
    flash.assert_message_match('Password/Verify Password do not match')


@pytest.mark.uncollect()
@pytest.mark.usefixtures('has_no_cloud_providers')
def test_providers_discovery_amazon():
    amazon_creds = get_credentials_from_config('cloudqe_amazon')
    discover(amazon_creds)
    flash.assert_message_match('Amazon Cloud Providers: Discovery successfully initiated')
    wait_for_a_provider()


@pytest.mark.usefixtures('has_no_cloud_providers')
def test_provider_add_with_bad_credentials(provider):
    """ Tests provider add with bad credentials

    Metadata:
        test_flag: crud
    """
    provider.credentials['default'] = get_credentials_from_config('bad_credentials')
    with error.expected('Login failed due to a bad username or password.'):
        provider.create(validate_credentials=True)


@pytest.mark.usefixtures('has_no_cloud_providers')
def test_provider_crud(provider):
    """ Tests provider add with good credentials

    Metadata:
        test_flag: crud
    """
    provider.create()
    provider.validate(db=False)

    old_name = provider.name
    with update(provider):
        provider.name = str(uuid.uuid4())  # random uuid

    with update(provider):
        provider.name = old_name  # old name

    provider.delete(cancel=False)
    provider.wait_for_delete()


def test_type_required_validation(request, soft_assert):
    """Test to validate type while adding a provider"""
    prov = Provider()

    request.addfinalizer(prov.delete_if_exists)
    if version.current_version() < "5.5":
        with error.expected('Type is required'):
            prov.create()
    else:
        pytest.sel.force_navigate("clouds_provider_new")
        fill(properties_form.name_text, "foo")
        soft_assert("ng-invalid-required" in properties_form.type_select.classes)
        soft_assert(not prov.add_provider_button.can_be_clicked)


def test_name_required_validation(request):
    """Tests to validate the name while adding a provider"""
    prov = EC2Provider(
        name=None,
        region='us-east-1')

    request.addfinalizer(prov.delete_if_exists)
    if version.current_version() < "5.5":
        with error.expected("Name can't be blank"):
            prov.create()
    else:
        # It must raise an exception because it keeps on the form
        with error.expected(FlashMessageException):
            prov.create()
        assert properties_form.name_text.angular_help_block == "Required"


def test_region_required_validation(request, soft_assert):
    """Tests to validate the region while adding a provider"""
    prov = EC2Provider(
        name=fauxfactory.gen_alphanumeric(5),
        region=None)

    request.addfinalizer(prov.delete_if_exists)
    if version.current_version() < "5.5":
        with error.expected('Region is not included in the list'):
            prov.create()
    else:
        with error.expected(FlashMessageException):
            prov.create()
        soft_assert("ng-invalid-required" in properties_form.amazon_region_select.classes)


def test_host_name_required_validation(request):
    """Test to validate the hostname while adding a provider"""
    prov = OpenStackProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=None,
        ip_address=fauxfactory.gen_ipaddr(prefix=[10]))

    request.addfinalizer(prov.delete_if_exists)
    if version.current_version() < "5.5":
        with error.expected("Host Name can't be blank"):
            prov.create()
    else:
        # It must raise an exception because it keeps on the form
        with error.expected(FlashMessageException):
            prov.create()
        assert properties_form.hostname_text.angular_help_block == "Required"


@pytest.mark.uncollectif(lambda: version.current_version() > '5.4')
def test_ip_address_required_validation(request):
    """Test to validate the ip address while adding a provider"""
    prov = OpenStackProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address=None)

    request.addfinalizer(prov.delete_if_exists)
    with error.expected("IP Address can't be blank"):
        prov.create()


def test_api_port_blank_validation(request):
    """Test to validate blank api port while adding a provider"""
    prov = OpenStackProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address=fauxfactory.gen_ipaddr(prefix=[10]),
        api_port='')

    request.addfinalizer(prov.delete_if_exists)
    if version.current_version() < "5.5":
        prov.create()
    else:
        # It must raise an exception because it keeps on the form
        with error.expected(FlashMessageException):
            prov.create()
        assert properties_form.api_port.angular_help_block == "Required"


def test_user_id_max_character_validation():
    cred = Credential(principal=fauxfactory.gen_alphanumeric(51))
    discover(cred)


def test_password_max_character_validation():
    password = fauxfactory.gen_alphanumeric(51)
    cred = Credential(
        principal=fauxfactory.gen_alphanumeric(5),
        secret=password,
        verify_secret=password)
    discover(cred)


def test_name_max_character_validation(request):
    """Test to validate max character for name field"""
    prov = EC2Provider(
        name=fauxfactory.gen_alphanumeric(255),
        region='us-east-1')

    request.addfinalizer(prov.delete_if_exists)
    prov.create()


def test_hostname_max_character_validation(request):
    """Test to validate max character for hostname field"""
    prov = OpenStackProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(255),
        ip_address=fauxfactory.gen_ipaddr(prefix=[10]))

    request.addfinalizer(prov.delete_if_exists)
    prov.create()


def test_ip_max_valid_character_validation(request):
    """Test to validate max character for ip address field with valid ip address"""
    prov = OpenStackProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address=fauxfactory.gen_ipaddr(prefix=[10]))

    request.addfinalizer(prov.delete_if_exists)
    prov.create()


def test_ip_max_invalid_character_validation(request):
    """Test to validate max character for ip address field using random string"""
    prov = OpenStackProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address=fauxfactory.gen_alphanumeric(15))

    request.addfinalizer(prov.delete_if_exists)
    prov.create()


def test_api_port_max_character_validation(request):
    """Test to validate max character for api port field"""
    prov = OpenStackProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address=fauxfactory.gen_ipaddr(prefix=[10]),
        api_port=fauxfactory.gen_alphanumeric(15))

    request.addfinalizer(prov.delete_if_exists)
    prov.create()
