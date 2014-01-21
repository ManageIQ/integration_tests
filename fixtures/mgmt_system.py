    # pylint: disable=E1101
import logging
import time

import pytest
from unittestzero import Assert

from utils.conf import cfme_data
from utils.providers import (
    infra_provider_type_map,
    cloud_provider_type_map,
    provider_factory,
    setup_infrastructure_provider
)

logger = logging.getLogger(__name__)


@pytest.fixture
def setup_infrastructure_providers(infra_providers_pg):
    '''Adds all infrastructure providers listed in cfme_data.yaml

    This includes both rhev and virtualcenter provider types

    vsphere5:
        name: vsphere55
        default_name: vsphere55
        credentials: cloudqe_vsphere55
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
        credentials: cloudqe_rhev32_71
        hostname: hostname.redhat.com
        ipaddress: 1.1.1.2
        server_zone: default
        type: rhevm
        discovery_range:
            start: 1.1.1.1
            end: 1.1.1.3

    '''
    # Does provider exist
    providers_to_add = []
    for provider, prov_data in cfme_data['management_systems'].iteritems():
        if prov_data['type'] not in infra_provider_type_map:
            # short out if we don't care about this provider type
            continue

        if not infra_providers_pg.quadicon_region.does_quadicon_exist(prov_data['name']):
            providers_to_add.append([provider, prov_data])

    for prov_args in providers_to_add:
        setup_infrastructure_provider(*prov_args)


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
    for provider, prov_data in cfme_data['management_systems'].iteritems():
        if prov_data['type'] not in cloud_provider_type_map:
            # short out if we don't care about this provider type
            continue

        prov_added = False
        cloud_providers_pg.taskbar_region.view_buttons.change_to_grid_view()
        Assert.true(cloud_providers_pg.taskbar_region.view_buttons.is_grid_view)
        if not (cloud_providers_pg.quadicon_region.quadicons and
                cloud_providers_pg.quadicon_region.does_quadicon_exist(prov_data['name'])):
            # add it
            add_pg = cloud_providers_pg.click_on_add_new_provider()
            add_pg.add_provider(prov_data)

            Assert.equal(cloud_providers_pg.flash.message,
                'Cloud Providers "%s" was saved' % prov_data['name'],
                'Flash message did not match')
            prov_added = True

            # wait for the quadicon to show up
            sleep_time = 0
            cloud_providers_pg.taskbar_region.view_buttons.change_to_grid_view()
            Assert.true(cloud_providers_pg.taskbar_region.view_buttons.is_grid_view)
            while not cloud_providers_pg.quadicon_region.does_quadicon_exist(
                    prov_data['name']):
                if sleep_time > 300:
                    raise Exception('timeout reached for provider icon to show up')
                cloud_providers_pg.selenium.refresh()
                sleep_time += 10
                time.sleep(10)

        # Are the credentials valid?
        cloud_providers_pg.taskbar_region.view_buttons.change_to_grid_view()
        Assert.true(cloud_providers_pg.taskbar_region.view_buttons.is_grid_view)
        prov_quadicon = cloud_providers_pg.quadicon_region.get_quadicon_by_title(
            prov_data['name'])
        valid_creds = prov_quadicon.valid_credentials
        if prov_added and not valid_creds:
            sleep_time = 0
            while not valid_creds:
                if sleep_time > 300:
                    raise Exception('timeout reached for valid provider credentials')
                cloud_providers_pg.selenium.refresh()
                prov_quadicon = cloud_providers_pg.quadicon_region.get_quadicon_by_title(
                    prov_data['name'])
                valid_creds = prov_quadicon.valid_credentials
                sleep_time += 10
                time.sleep(10)
        elif not prov_quadicon.valid_credentials:
            # update them
            cloud_providers_pg.select_provider(prov_data['name'])
            Assert.equal(len(cloud_providers_pg.quadicon_region.selected), 1,
                'More than one quadicon was selected')
            prov_edit_pg = cloud_providers_pg.click_on_edit_providers()
            prov_edit_pg.edit_provider(prov_data)
        prov_data['request'] = provider
        if prov_added:
            cloud_providers_pg.wait_for_provider_or_timeout(prov_data)
        cloud_providers_pg.header.site_navigation_menu('Clouds').\
            sub_navigation_menu('Providers').click()


@pytest.fixture(scope='module')  # IGNORE:E1101
def mgmt_sys_api_clients(cfme_data):
    '''Returns a list of management system api clients'''
    clients = {}
    for sys_name in cfme_data['management_systems']:
        if sys_name in clients:
            # Overlapping sys_name entry in cfme_data.yaml
            logger.warning('Overriding existing entry for %s.' % sys_name)
        clients[sys_name] = provider_factory(sys_name)
    return clients
