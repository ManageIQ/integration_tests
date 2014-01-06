# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621

import pytest
import cfme.web_ui.flash as flash
from unittestzero import Assert
from cfme.cloud.provider import Provider

CURRENT_PAGE_NOT_MATCHED = 'Current page not what was expected'
FLASH_MESSAGE_NOT_MATCHED = 'Flash message did not match expected value'
DETAIL_NOT_MATCHED_TEMPLATE = '%s did not match'


@pytest.fixture(params=['ec2east', 'openstack'])
def provider_data(request, cfme_data):
    '''Returns management system data from cfme_data'''
    param = request.param
    prov_data = cfme_data.data['management_systems'][param]
    prov_data['request'] = param
    
    return prov_data


@pytest.fixture
def provider(request, cloud_providers_pg, provider_data):
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


def test_that_checks_flash_when_add_cancelled():
    '''Tests that the flash message is correct when add is cancelled'''
    prov = Provider()
    prov.create(cancel=True)
    Assert.equal(flash.get_message(),
                 'Add of new Cloud Provider was cancelled by the user',
                 FLASH_MESSAGE_NOT_MATCHED)
