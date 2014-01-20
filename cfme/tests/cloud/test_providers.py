# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621

import pytest
import cfme.web_ui.flash as flash
from cfme.cloud.provider as provider


@pytest.fixture(params=['ec2east', 'openstack'])
def (request, cfme_data):
    '''Returns management system data from cfme_data'''
    param = request.param
    return provider.get_from_config(request.param)


@pytest.fixture
def my_provider(request, cloud_providers_pg, provider_data):
    '''Create a management system

    Creates a management system based on the data from cfme_data.
    Ideally, this fixture would clean up after itself, but currently
    the only way to do that is via the UI, and we lose the selenium session
    before the finalizer gets an opportunity to run.

    This fixture will modify the db directly in the near future'''
    prov_add_pg = cloud_providers_pg.click_on_add_new_provider()

    # Returns prov_pg object
    prov_add_pg.add_provider(provider_data)

    # TODO: Finalizer doesn't actually work. The selenium session is
    #       killed prior to its running.
    # def fin():
    #     cloud_providers_pg = mgmtsys_page.header.site_navigation_menu(
    #             "Infrastructure").sub_navigation_menu(
    #                     "Management Systems").click()
    #     ms_name = provider_data[name_property]
    #     cloud_providers_pg.wait_for_provider_or_timeout(ms_name)
    #     cloud_providers_pg.select_provider(ms_name)
    #     cloud_providers_pg.click_on_remove_provider()
    # request.addfinalizer(fin)
    return provider_data


@pytest.fixture
def has_no_providers(db_session):
    '''Clears all management systems from an applicance

    This is a destructive fixture. It will clear all managements systems from
    the current appliance.
    '''
    import db
    db_session.query(db.ExtManagementSystem).delete()
    db_session.commit()

pytestmark = [pytest.mark.usefixtures("logged_in")]


def test_that_checks_flash_with_empty_discovery_form():
    '''Tests that the flash message is correct when discovery form is
    empty
    '''
    discover(None)
    flash.assert_message_match('User ID is required')


def test_that_checks_flash_when_discovery_cancelled():
    '''Tests that the flash message is correct when discovery is cancelled
    '''
    discover(None, cancel=True)
    flash.assert_message_match('Amazon Cloud Providers Discovery was cancelled by the user')


@pytest.mark.usefixtures('has_no_providers')
def test_provider_edit(myprovider):
    '''Tests that editing a management system shows the proper detail
    after an edit
    '''
    myprovider.create()
    # TODO finish this

def test_that_checks_flash_when_add_cancelled():
    '''Tests that the flash message is correct when add is cancelled'''
    prov = Provider()
    prov.create(cancel=True)
    flash.assert_message_match('Add of new Cloud Provider was cancelled by the user')
