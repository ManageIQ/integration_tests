# pylint: disable=E1101
import logging
import time
import random
import pytest
from unittestzero import Assert

from common.mgmt_system import VMWareSystem, RHEVMSystem, EC2System

logger = logging.getLogger(__name__)
@pytest.fixture
def setup_infrastructure_providers(infra_providers_pg, cfme_data):
    '''Adds all infrastructure providers listed in cfme_data.yaml

    This includes both rhev and virtualcenter provider types

    vsphere5:
        name: vsphere5
        default_name: vsphere5
        credentials: cloudqe_vsphere5
        hostname: hostname.redhat.com
        ipaddress: 1.1.1.2
        host_vnc_port:
            start: 5900
            end: 5980
        server_zone: default
        type: virtualcenter
        discovery_range:
            start: 1.1.1.1
            end: 1.1.1.3
    rhevm32:
        name: RHEV 3.2
        credentials: cloudqe_rhev32
        hostname: hostname.redhat.com
        ipaddress: 1.1.1.2
        server_zone: default
        type: rhevm
        discovery_range:
            start: 1.1.1.1
            end: 1.1.1.3

    '''
    # Does provider exist
    for provider in cfme_data.data['management_systems']:
        if cfme_data.data['management_systems'][provider]["type"] == 'virtualcenter' or \
                cfme_data.data['management_systems'][provider]["type"] == 'rhevm':
            prov_data = cfme_data.data['management_systems'][provider]
            prov_cred = infra_providers_pg.testsetup.credentials[prov_data['credentials']]
            prov_added = False
            infra_providers_pg.taskbar_region.view_buttons.change_to_grid_view()
            Assert.true(infra_providers_pg.taskbar_region.view_buttons.is_grid_view)
            if (len(infra_providers_pg.quadicon_region.quadicons) == 0) \
                    or not infra_providers_pg.quadicon_region.does_quadicon_exist(
                            prov_data['name']):
                # add it
                add_pg = infra_providers_pg.click_on_add_new_provider()
                add_pg.add_provider(prov_data)
                Assert.equal(infra_providers_pg.flash.message,
                        'Infrastructure Providers "%s" was saved'
                                % prov_data['name'],
                        'Flash message did not match')
                prov_added = True

                # wait for the quadicon to show up
                sleep_time = 1
                infra_providers_pg.taskbar_region.view_buttons.change_to_grid_view()
                Assert.true(infra_providers_pg.taskbar_region.view_buttons.is_grid_view)
                while not infra_providers_pg.quadicon_region.does_quadicon_exist(
                        prov_data['name']):
                    infra_providers_pg.selenium.refresh()
                    time.sleep(sleep_time)
                    sleep_time *= 2
                    if sleep_time > 90:
                        raise Exception(
                                'timeout reached for provider icon to show up')

            # Are the credentials valid?
            infra_providers_pg.taskbar_region.view_buttons.change_to_grid_view()
            Assert.true(infra_providers_pg.taskbar_region.view_buttons.is_grid_view)
            prov_quadicon = infra_providers_pg.quadicon_region.get_quadicon_by_title(
                    prov_data['name'])
            valid_creds = prov_quadicon.valid_credentials
            if prov_added and not valid_creds:
                sleep_time = 1
                while not valid_creds:
                    infra_providers_pg.selenium.refresh()
                    time.sleep(sleep_time)
                    prov_quadicon = infra_providers_pg.quadicon_region.get_quadicon_by_title(
                            prov_data['name'])
                    valid_creds = prov_quadicon.valid_credentials
                    sleep_time *= 2
                    if sleep_time > 90:
                        raise Exception(
                                'timeout reached for valid provider credentials')
            elif not prov_quadicon.valid_credentials:
                # update them
                infra_providers_pg.select_provider(prov_data['name'])
                Assert.equal(len(infra_providers_pg.quadicon_region.selected), 1,
                        'More than one quadicon was selected')
                prov_edit_pg = infra_providers_pg.click_on_edit_providers()
                prov_edit_pg.edit_provider(prov_data)

# there is a partially implemented db fixture at
#       https://github.com/dajohnso/cfme_tests/tree/add_cloud_provider_db_fixture
@pytest.fixture
def setup_cloud_providers(cloud_providers_pg, cfme_data):
    '''Adds all cloud providers listed in cfme_data.yaml

    This include both ec2 and openstack providers types

    openstack:
        name: provider_name
        hostname: hostname.redhat.com
        ipaddress: 1.1.1.1
        port: 5000
        credentials: cloudqe_openstack
        server_zone: default
        type: openstack
    ec2east:
        name: ec2-east
        region: us-east-1
        credentials: cloudqe_amazon
        server_zone: default
        type: ec2

    '''
    # Does provider exist
    for provider in cfme_data.data['management_systems']:
        if cfme_data.data['management_systems'][provider]["type"] == 'openstack' or \
                cfme_data.data['management_systems'][provider]["type"] == 'ec2':
            prov_data = cfme_data.data['management_systems'][provider]
            prov_cred = cloud_providers_pg.testsetup.credentials[prov_data['credentials']]
            prov_added = False
            cloud_providers_pg.taskbar_region.view_buttons.change_to_grid_view()
            Assert.true(cloud_providers_pg.taskbar_region.view_buttons.is_grid_view)
            if (len(cloud_providers_pg.quadicon_region.quadicons) == 0) \
                    or not cloud_providers_pg.quadicon_region.does_quadicon_exist(
                            prov_data['name']):
                # add it
                add_pg = cloud_providers_pg.click_on_add_new_provider()
                add_pg.add_provider(prov_data)
                
                Assert.equal(cloud_providers_pg.flash.message,
                        'Cloud Providers "%s" was saved'
                                % prov_data['name'],
                        'Flash message did not match')
                prov_added = True

                # wait for the quadicon to show up
                sleep_time = 1
                cloud_providers_pg.taskbar_region.view_buttons.change_to_grid_view()
                Assert.true(cloud_providers_pg.taskbar_region.view_buttons.is_grid_view)
                while not cloud_providers_pg.quadicon_region.does_quadicon_exist(
                        prov_data['name']):
                    cloud_providers_pg.selenium.refresh()
                    time.sleep(sleep_time)
                    sleep_time *= 2
                    if sleep_time > 90:
                        raise Exception(
                                'timeout reached for provider icon to show up')

            # Are the credentials valid?
            cloud_providers_pg.taskbar_region.view_buttons.change_to_grid_view()
            Assert.true(cloud_providers_pg.taskbar_region.view_buttons.is_grid_view)
            prov_quadicon = cloud_providers_pg.quadicon_region.get_quadicon_by_title(
                    prov_data['name'])
            valid_creds = prov_quadicon.valid_credentials
            if prov_added and not valid_creds:
                sleep_time = 1
                while not valid_creds:
                    cloud_providers_pg.selenium.refresh()
                    time.sleep(sleep_time)
                    prov_quadicon = cloud_providers_pg.quadicon_region.get_quadicon_by_title(
                            prov_data['name'])
                    valid_creds = prov_quadicon.valid_credentials
                    sleep_time *= 2
                    if sleep_time > 150:
                        raise Exception(
                                'timeout reached for valid provider credentials')
            elif not prov_quadicon.valid_credentials:
                # update them
                cloud_providers_pg.select_provider(prov_data['name'])
                Assert.equal(len(cloud_providers_pg.quadicon_region.selected), 1,
                        'More than one quadicon was selected')
                prov_edit_pg = cloud_providers_pg.click_on_edit_providers()
                prov_edit_pg.edit_provider(prov_data)


@pytest.fixture(scope='module')  # IGNORE:E1101
def mgmt_sys_api_clients(mozwebqa, cfme_data):
    '''Returns a list of management system api clients'''
    clients = {}
    for sys_name, mgmt_sys in cfme_data.data['management_systems'].items():
        cred = mgmt_sys['credentials'].strip()
        host = mgmt_sys['ipaddress']
        user = mozwebqa.credentials[cred]['username']
        pwd = mozwebqa.credentials[cred]['password']
        sys_type = mgmt_sys['type']

        if 'virtual' in sys_type.lower():
            client = VMWareSystem(
                hostname=host,
                username=user,
                password=pwd
            )
        elif 'rhevm' in sys_type.lower():
            client = RHEVMSystem(
                hostname=host,
                username=user,
                password=pwd
            )
        elif 'ec2' in sys_type.lower():
            client = EC2System(
                access_key_id=user,
                secret_access_key=pwd
            )
        else:
            logger.info("Can't create client for %s, ignoring..." % sys_name)
            continue

        if sys_name in clients:
            # Overlapping sys_name entry in cfme_data.yaml
            logger.warning('Overriding existing entry for %s.' % sys_name)
        clients[sys_name] = client
        # unbind the 'client' identifier for the next iteration
        del client

    return clients


