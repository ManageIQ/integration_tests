'''
@author: bcrochet
'''
# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621

import pytest
import time
from unittestzero import Assert

CURRENT_PAGE_NOT_MATCHED = 'Current page not what was expected'
FLASH_MESSAGE_NOT_MATCHED = 'Flash message did not match expected value'
DETAIL_NOT_MATCHED_TEMPLATE = '%s did not match'

@pytest.fixture(params=['vsphere5', 'rhevm31'])  # IGNORE:E1101
def provider_data(request, cfme_data):
    '''Returns management system data from cfme_data'''
    param = request.param
    return cfme_data.data['management_systems'][param]

@pytest.fixture
def provider(request, infra_providers_pg, provider_data):
    '''Create a management system

    Creates a management system based on the data from cfme_data.
    Ideally, this fixture would clean up after itself, but currently
    the only way to do that is via the UI, and we lose the selenium session
    before the finalizer gets an opportunity to run.

    This fixture will modify the db directly in the near future'''
    prov_add_pg = infra_providers_pg.click_on_add_new_provider()
    prov_pg = prov_add_pg.add_provider(provider_data)
    # TODO: Finalizer doesn't actually work. The selenium session is
    #       killed prior to its running.
    # def fin():
    #     infra_providers_pg = mgmtsys_page.header.site_navigation_menu(
    #             "Infrastructure").sub_navigation_menu(
    #                     "Management Systems").click()
    #     ms_name = provider_data[name_property]
    #     infra_providers_pg.wait_for_provider_or_timeout(ms_name)
    #     infra_providers_pg.select_provider(ms_name)
    #     infra_providers_pg.click_on_remove_provider()
    # request.addfinalizer(fin)
    return provider_data

@pytest.fixture
def has_no_providers(db_session):
    '''Clears all management systems from an applicance

    This is a destructive fixture. It will clear all managements systems from
    the current appliance.
    '''
    import db
    session = db_session
    session.query(db.ExtManagementSystem).delete()
    session.commit()

@pytest.mark.usefixtures('maximized')  # IGNORE:E1101
class TestInfrastructureProviders:
    @pytest.mark.nondestructive  # IGNORE:E1101
    def test_that_checks_flash_with_no_provider_types_checked(self,
            infra_providers_pg):
        '''Tests that the flash message is correct when no management systems
        are selected
        '''
        prov_pg = infra_providers_pg
        Assert.true(prov_pg.is_the_current_page)
        prov_discover_pg = prov_pg.click_on_discover_providers()
        prov_discover_pg.click_on_start()
        Assert.equal(prov_discover_pg.flash.message,
                'At least 1 item must be selected for discovery',
                FLASH_MESSAGE_NOT_MATCHED)

    @pytest.mark.nondestructive  # IGNORE:E1101
    def test_that_checks_flash_when_discovery_cancelled(self,
            infra_providers_pg):
        '''Tests that the flash message is correct when discovery is cancelled
        '''
        prov_pg = infra_providers_pg
        Assert.true(prov_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
        prov_discover_pg = prov_pg.click_on_discover_providers()
        prov_pg = prov_discover_pg.click_on_cancel()
        Assert.true(prov_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
        Assert.equal(prov_pg.flash.message,
                'Infrastructure Providers Discovery was cancelled by the user',
                FLASH_MESSAGE_NOT_MATCHED)

    @pytest.mark.nondestructive
    def test_that_checks_flash_when_add_cancelled(self, infra_providers_pg):
        '''Tests that the flash message is correct when add is cancelled'''
        prov_pg = infra_providers_pg
        Assert.true(prov_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
        prov_add_pg = prov_pg.click_on_add_new_provider()
        prov_pg = prov_add_pg.click_on_cancel()
        Assert.true(prov_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
        Assert.equal(prov_pg.flash.message,
                'Add of new Infrastructure Provider was cancelled by the user',
                FLASH_MESSAGE_NOT_MATCHED)

    @pytest.mark.usefixtures('has_no_providers')
    def test_provider_edit(self,
            infra_providers_pg,
            provider,
            random_uuid_as_string):
        '''Tests that editing a management system shows the proper detail
        after an edit
        '''
        prov_pg = infra_providers_pg
        edit_name = random_uuid_as_string
        prov_pg.taskbar_region.view_buttons.change_to_grid_view()
        Assert.true(prov_pg.taskbar_region.view_buttons.is_grid_view)
        prov_pg.select_provider(provider['name'])
        Assert.equal(len(prov_pg.quadicon_region.selected), 1,
                'More than one quadicon was selected')
        prov_edit_pg = prov_pg.click_on_edit_providers()
        provider['edit_name'] = edit_name
        prov_detail_pg = prov_edit_pg.edit_provider(provider)
        Assert.equal(prov_detail_pg.flash.message,
                'Infrastructure Provider "%s" was saved' \
                % provider['edit_name'], FLASH_MESSAGE_NOT_MATCHED)
        Assert.equal(prov_detail_pg.name, provider['edit_name'],
                DETAIL_NOT_MATCHED_TEMPLATE % 'Edited name')
        Assert.equal(prov_detail_pg.hostname, provider['hostname'],
                DETAIL_NOT_MATCHED_TEMPLATE % 'Hostname')
        Assert.equal(prov_detail_pg.zone, provider['server_zone'],
                DETAIL_NOT_MATCHED_TEMPLATE % 'Server zone')
        if 'host_vnc_port' in provider:
            Assert.equal(prov_detail_pg.vnc_port_range,
                    provider['host_vnc_port'],
                    DETAIL_NOT_MATCHED_TEMPLATE % 'VNC port range')

    @pytest.mark.usefixtures('has_no_providers')
    def test_provider_add(
            self, infra_providers_pg, provider_data, soap_client):
        '''Tests adding a new management system
        '''
        prov_pg = infra_providers_pg
        prov_add_pg = prov_pg.click_on_add_new_provider()
        prov_pg = prov_add_pg.add_provider(provider_data)
        Assert.equal(prov_pg.flash.message,
                'Infrastructure Providers "%s" was saved' \
                 % provider_data['name'],
                FLASH_MESSAGE_NOT_MATCHED)

    @pytest.mark.usefixtures('has_no_providers')
    def test_provider_add_with_bad_credentials(
            self, infra_providers_pg, provider_data):
        '''Tests adding a new management system with bad credentials
        '''
        prov_pg = infra_providers_pg
        prov_add_pg = prov_pg.click_on_add_new_provider()
        provider_data['credentials'] = 'bad_credentials'
        prov_add_pg = prov_add_pg.add_provider_with_bad_credentials(
                provider_data)
        Assert.equal(prov_add_pg.flash.message,
            'Cannot complete login due to an incorrect user name or password.',
            FLASH_MESSAGE_NOT_MATCHED)

    @pytest.mark.usefixtures('has_no_providers')
    def test_providers_discovery_starts(
            self, infra_providers_pg, provider_data):
        '''Tests the start of a management system discovery
        '''
        prov_pg = infra_providers_pg
        Assert.true(prov_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
        prov_discovery_pg = prov_pg.click_on_discover_providers()
        Assert.true(prov_discovery_pg.is_the_current_page,
                CURRENT_PAGE_NOT_MATCHED)
        prov_pg = prov_discovery_pg.discover_infrastructure_providers(
                provider_data['type'],
                provider_data['discovery_range']['start'],
                provider_data['discovery_range']['end'])
        Assert.true(prov_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
        Assert.equal(prov_pg.flash.message,
                'Infrastructure Providers: Discovery successfully initiated',
                FLASH_MESSAGE_NOT_MATCHED)
