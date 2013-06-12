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
def management_system_data(request, cfme_data, mgmtsys_page):
    '''Returns management system data from cfme_data'''
    param = request.param
    return cfme_data.data['management_systems'][param]

@pytest.fixture
def management_system(request, mgmtsys_page, management_system_data):
    '''Create a management system

    Creates a management system based on the data from cfme_data.
    Ideally, this fixture would clean up after itself, but currently 
    the only way to do that is via the UI, and we lose the selenium session
    before the finalizer gets an opportunity to run.

    This fixture will modify the db directly in the near future'''
    ms_pg = mgmtsys_page.header.site_navigation_menu(
            'Infrastructure').sub_navigation_menu(
                    'Management Systems').click()
    msadd_pg = ms_pg.click_on_add_new_management_system()
    ms_pg = msadd_pg.add_management_system(management_system_data)
    # TODO: Finalizer doesn't actually work. The selenium session is 
    #       killed prior to its running.
    # def fin():
    #     ms_pg = mgmtsys_page.header.site_navigation_menu(
    #             "Infrastructure").sub_navigation_menu(
    #                     "Management Systems").click()
    #     ms_name = management_system_data[name_property]
    #     ms_pg.wait_for_management_system_or_timeout(ms_name)
    #     ms_pg.select_management_system(ms_name)
    #     ms_pg.click_on_remove_management_system()
    # request.addfinalizer(fin)
    return management_system_data

@pytest.fixture  # IGNORE:E1101
def has_no_management_systems(db_session):
    '''Clears all management systems from an applicance

    This is a destructive fixture. It will clear all managements systems from
    the current appliance.
    '''
    import db
    session = db_session
    session.query(db.ExtManagementSystem).delete()
    session.commit()

@pytest.mark.usefixtures('maximized')  # IGNORE:E1101
class TestManagementSystems:
    @pytest.mark.nondestructive  # IGNORE:E1101 
    def test_that_checks_flash_with_no_management_types_checked(self,
            mgmtsys_page):
        '''Tests that the flash message is correct when no management systems
        are selected
        '''
        ms_pg = mgmtsys_page
        Assert.true(ms_pg.is_the_current_page)
        msd_pg = ms_pg.click_on_discover_management_systems()
        msd_pg.click_on_start()
        Assert.equal(msd_pg.flash.message,
                'At least 1 item must be selected for discovery',
                FLASH_MESSAGE_NOT_MATCHED)

    @pytest.mark.nondestructive  # IGNORE:E1101
    def test_that_checks_flash_when_discovery_cancelled(self, mgmtsys_page):
        '''Tests that the flash message is correct when discovery is cancelled
        '''
        ms_pg = mgmtsys_page
        Assert.true(ms_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
        msd_pg = ms_pg.click_on_discover_management_systems()
        ms_pg = msd_pg.click_on_cancel()
        Assert.true(ms_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
        Assert.equal(ms_pg.flash.message,
                'Management System Discovery was cancelled by the user',
                FLASH_MESSAGE_NOT_MATCHED)

    @pytest.mark.nondestructive
    def test_that_checks_flash_when_add_cancelled(self, mgmtsys_page):
        '''Tests that the flash message is correct when add is cancelled'''
        ms_pg = mgmtsys_page
        Assert.true(ms_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
        msa_pg = ms_pg.click_on_add_new_management_system()
        ms_pg = msa_pg.click_on_cancel()
        Assert.true(ms_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
        Assert.equal(ms_pg.flash.message,
                'Add of new Management System was cancelled by the user',
                FLASH_MESSAGE_NOT_MATCHED)

    @pytest.mark.usefixtures('has_no_management_systems')
    def test_edit_management_system(self,
            mgmtsys_page,
            management_system,
            random_uuid_as_string):
        '''Tests that editing a management system shows the proper detail
        after an edit
        '''
        ms_pg = mgmtsys_page
        edit_name = random_uuid_as_string
        ms_pg.select_management_system(management_system['name'])
        Assert.equal(len(ms_pg.quadicon_region.selected), 1,
                'More than one quadicon was selected')
        mse_pg = ms_pg.click_on_edit_management_systems()
        management_system['edit_name'] = edit_name
        msdetail_pg = mse_pg.edit_management_system(management_system)
        Assert.equal(msdetail_pg.flash.message,
                'Management System "%s" was saved' \
                % management_system['edit_name'], FLASH_MESSAGE_NOT_MATCHED)
        Assert.equal(msdetail_pg.name, management_system['edit_name'],
                DETAIL_NOT_MATCHED_TEMPLATE % 'Edited name')
        Assert.equal(msdetail_pg.hostname, management_system['hostname'],
                DETAIL_NOT_MATCHED_TEMPLATE % 'Hostname')
        Assert.equal(msdetail_pg.zone, management_system['server_zone'],
                DETAIL_NOT_MATCHED_TEMPLATE % 'Server zone')
        if 'host_vnc_port' in management_system:
            Assert.equal(msdetail_pg.vnc_port_range,
                    management_system['host_vnc_port'],
                    DETAIL_NOT_MATCHED_TEMPLATE % 'VNC port range')

    @pytest.mark.usefixtures('has_no_management_systems')
    def test_management_system_add(
            self, mgmtsys_page, management_system_data, soap_client):
        '''Tests adding a new management system
        '''
        ms_pg = mgmtsys_page
        msadd_pg = ms_pg.click_on_add_new_management_system()
        ms_pg = msadd_pg.add_management_system(management_system_data)
        Assert.equal(ms_pg.flash.message,
                'Management System "%s" was saved' \
                 % management_system_data['name'],
                FLASH_MESSAGE_NOT_MATCHED)

    @pytest.mark.usefixtures('has_no_management_systems')    
    def test_management_system_add_with_bad_credentials(
            self, mgmtsys_page, management_system_data):
        '''Tests adding a new management system with bad credentials
        '''
        ms_pg = mgmtsys_page
        msadd_pg = ms_pg.click_on_add_new_management_system()
        management_system_data['credentials'] = 'bad_credentials'
        msadd_pg = msadd_pg.add_management_system_with_bad_credentials(
                management_system_data)
        Assert.equal(msadd_pg.flash.message,
            'Cannot complete login due to an incorrect user name or password.',
            FLASH_MESSAGE_NOT_MATCHED)

    @pytest.mark.usefixtures('has_no_management_systems')
    def test_discover_management_systems_starts(
            self, mgmtsys_page, management_system_data):
        '''Tests the start of a management system discovery
        '''
        ms_pg = mgmtsys_page
        Assert.true(ms_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
        msd_pg = ms_pg.click_on_discover_management_systems()
        Assert.true(msd_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
        ms_pg = msd_pg.discover_systems(
                management_system_data['type'],
                management_system_data['discovery_range']['start'],
                management_system_data['discovery_range']['end'])
        Assert.true(ms_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
        Assert.equal(ms_pg.flash.message,
                'Management System: Discovery successfully initiated',
                FLASH_MESSAGE_NOT_MATCHED)
