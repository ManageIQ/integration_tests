# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621

import pytest
import cfme.web_ui.flash as flash
from cfme.cloud import provider
from utils.update import update
import uuid
import utils.error as error


@pytest.fixture(params=['ec2east', 'openstack'])
def provider_data(request, cfme_data):
    """ Returns management system data from cfme_data"""
    return provider.get_from_config(request.param)


@pytest.fixture
def has_no_providers(db_session):
    """ Clears all management systems from an applicance

    This is a destructive fixture. It will clear all managements systems from
    the current appliance.
    """
    import db
    db_session.query(db.ExtManagementSystem).delete()
    db_session.commit()

pytestmark = [pytest.mark.usefixtures("logged_in")]


def test_that_checks_flash_with_empty_discovery_form():
    """ Tests that the flash message is correct when discovery form is empty."""
    provider.discover(None)
    flash.assert_message_match('User ID is required')


def test_that_checks_flash_when_discovery_cancelled():
    """ Tests that the flash message is correct when discovery is cancelled."""
    provider.discover(None, cancel=True)
    flash.assert_message_match('Amazon Cloud Providers Discovery was cancelled by the user')


@pytest.mark.usefixtures('has_no_providers')
def test_provider_add(provider_data):
    """ Tests that a provider can be added """
    provider_data.create()
    flash.assert_message_match('Cloud Providers "%s" was saved' % provider_data.name)


@pytest.mark.usefixtures('has_no_providers')
def test_provider_add_with_bad_credentials(provider_data):
    provider_data.credentials = provider.get_credentials_from_config('bad_credentials')
    with error.expected('Login failed due to a bad username or password.'):
        provider_data.create(validate_credentials=True)


@pytest.mark.usefixtures('has_no_providers')
def test_provider_edit(provider_data):
    """ Tests that editing a management system shows the proper detail after an edit."""
    provider_data.create()
    with update(provider_data) as provider_data:
        provider_data.name = str(uuid.uuid4())  # random uuid

    flash.assert_message_match('Cloud Provider "%s" was saved' % provider_data.name)


def test_that_checks_flash_when_add_cancelled():
    """Tests that the flash message is correct when add is cancelled."""
    prov = provider.EC2Provider()
    prov.create(cancel=True)
    flash.assert_message_match('Add of new Cloud Provider was cancelled by the user')
