# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621
import uuid

import pytest

import cfme.web_ui.flash as flash
import utils.error as error
from cfme.cloud import provider
from utils import testgen
from utils.update import update

pytest_generate_tests = testgen.generate(testgen.cloud_providers, scope="module")


def test_that_checks_flash_with_empty_discovery_form():
    """ Tests that the flash message is correct when discovery form is empty."""
    provider.discover(None)
    flash.assert_message_match('User ID is required')


def test_that_checks_flash_when_discovery_cancelled():
    """ Tests that the flash message is correct when discovery is cancelled."""
    provider.discover(None, cancel=True)
    flash.assert_message_match('Amazon Cloud Providers Discovery was cancelled by the user')


def test_that_checks_flash_when_add_cancelled():
    """Tests that the flash message is correct when add is cancelled."""
    prov = provider.EC2Provider()
    prov.create(cancel=True)
    flash.assert_message_match('Add of new Cloud Provider was cancelled by the user')


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
