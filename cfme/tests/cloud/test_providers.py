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
    Provider, OpenStackProvider, prop_region)
from cfme.web_ui import fill, flash
from utils import testgen
from utils.providers import get_credentials_from_config
from utils.update import update

pytest_generate_tests = testgen.generate(testgen.cloud_providers, scope="function")


def test_empty_discovery_form_validation():
    """ Tests that the flash message is correct when discovery form is empty."""
    discover(None, d_type="Amazon")
    ident = 'Username'
    flash.assert_message_match('{} is required'.format(ident))


def test_discovery_cancelled_validation():
    """ Tests that the flash message is correct when discovery is cancelled."""
    discover(None, cancel=True, d_type="Amazon")
    msg = 'Cloud Providers Discovery was cancelled by the user'
    flash.assert_message_match(msg)


def test_add_cancelled_validation(request):
    """Tests that the flash message is correct when add is cancelled."""
    prov = EC2Provider()
    request.addfinalizer(prov.delete_if_exists)
    prov.create(cancel=True)
    flash.assert_message_match('Add of Cloud Provider was cancelled by the user')


def test_password_mismatch_validation():
    cred = Credential(
        principal=fauxfactory.gen_alphanumeric(5),
        secret=fauxfactory.gen_alphanumeric(5),
        verify_secret=fauxfactory.gen_alphanumeric(7))

    discover(cred, d_type="Amazon")
    flash.assert_message_match('Password/Verify Password do not match')


@pytest.mark.uncollect()
@pytest.mark.usefixtures('has_no_cloud_providers')
def test_providers_discovery_amazon():
    amazon_creds = get_credentials_from_config('cloudqe_amazon')
    discover(amazon_creds, d_type="Amazon")
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
    provider.validate_stats(ui=True)

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
    pytest.sel.force_navigate("clouds_provider_new")
    fill(prop_region.name_text, "foo")
    soft_assert("ng-invalid-required" in prop_region.type_select.classes)
    soft_assert(not prov.add_provider_button.can_be_clicked)


def test_name_required_validation(request):
    """Tests to validate the name while adding a provider"""
    prov = EC2Provider(
        name=None,
        region='us-east-1')

    request.addfinalizer(prov.delete_if_exists)
    # It must raise an exception because it keeps on the form
    with error.expected(FlashMessageException):
        prov.create()
    assert prop_region.name_text.angular_help_block == "Required"


def test_region_required_validation(request, soft_assert):
    """Tests to validate the region while adding a provider"""
    prov = EC2Provider(
        name=fauxfactory.gen_alphanumeric(5),
        region=None)

    request.addfinalizer(prov.delete_if_exists)
    with error.expected(FlashMessageException):
        prov.create()
    soft_assert("ng-invalid-required" in prop_region.amazon_region_select.classes)


def test_host_name_required_validation(request):
    """Test to validate the hostname while adding a provider"""
    prov = OpenStackProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=None,
        ip_address=fauxfactory.gen_ipaddr(prefix=[10]))

    request.addfinalizer(prov.delete_if_exists)
    # It must raise an exception because it keeps on the form
    with error.expected(FlashMessageException):
        prov.create()
    assert prov.prop_region.hostname_text.angular_help_block == "Required"


def test_ip_address_required_validation(request):
    """Test to validate the ip address while adding a provider"""
    prov = OpenStackProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address=None)

    request.addfinalizer(prov.delete_if_exists)
    with error.expected("IP Address can't be blank"):
        prov.create()
    assert prop_region.hostname_text.angular_help_block == "Required"


def test_api_port_blank_validation(request):
    """Test to validate blank api port while adding a provider"""
    prov = OpenStackProvider(
        name=fauxfactory.gen_alphanumeric(5),
        hostname=fauxfactory.gen_alphanumeric(5),
        ip_address=fauxfactory.gen_ipaddr(prefix=[10]),
        api_port='')

    request.addfinalizer(prov.delete_if_exists)
    # It must raise an exception because it keeps on the form
    with error.expected(FlashMessageException):
        prov.create()
    assert prop_region.api_port.angular_help_block == "Required"


def test_user_id_max_character_validation():
    cred = Credential(principal=fauxfactory.gen_alphanumeric(51))
    discover(cred, d_type="Amazon")


def test_password_max_character_validation():
    password = fauxfactory.gen_alphanumeric(51)
    cred = Credential(
        principal=fauxfactory.gen_alphanumeric(5),
        secret=password,
        verify_secret=password)
    discover(cred, d_type="Amazon")


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


@pytest.mark.meta(blockers=[1278036])
def test_openstack_provider_has_api_version():
    """Check whether the Keystone API version field is present for Openstack."""
    prov = Provider()
    pytest.sel.force_navigate("clouds_provider_new")
    fill(prop_region.prop_region, {"type_select": "OpenStack"})
    pytest.sel.wait_for_ajax()
    assert pytest.sel.is_displayed(
        prov.prop_region.api_version), "API version select is not visible"
