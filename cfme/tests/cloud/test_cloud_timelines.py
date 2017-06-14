# -*- coding: utf-8 -*-
import pytest
from time import sleep

from cfme.cloud.availability_zone import AvailabilityZone
from cfme.cloud.instance import Instance
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.cloud.provider.ec2 import EC2Provider
from utils import testgen, version
from utils.appliance.implementations.ui import navigate_to
from utils.generators import random_vm_name
from utils.log import logger
from utils.wait import wait_for


pytestmark = [pytest.mark.tier(2),
              pytest.mark.uncollectif(lambda provider: provider.one_of(EC2Provider) and
                                      version.current_version() < '5.8'),
              pytest.mark.usefixtures("setup_provider_modscope")]
pytest_generate_tests = testgen.generate([AzureProvider, OpenStackProvider, EC2Provider],
                                         scope="module")


def ec2_sleep():
    # CFME currently obtains events from AWS Config thru AWS SNS
    # EC2 Config creates config diffs apprx. every 10 minutes
    # This workaround is needed until CFME starts using CloudWatch + CloudTrail instead
    sleep(900)


@pytest.fixture(scope="module")
def new_instance(request, provider):
    instance = Instance.factory(random_vm_name("timelines", max_length=16), provider)

    request.addfinalizer(instance.delete_from_provider)

    if not provider.mgmt.does_vm_exist(instance.name):
        logger.info("deploying %s on provider %s", instance.name, provider.key)
        instance.create_on_provider(allow_skip="default", find_in_cfme=True)
        if instance.provider.one_of(EC2Provider):
            ec2_sleep()
    return instance


@pytest.fixture(scope="module")
def gen_events(new_instance):
    logger.debug('Starting, stopping VM')
    mgmt = new_instance.provider.mgmt
    mgmt.stop_vm(new_instance.name)
    if new_instance.provider.one_of(EC2Provider):
        ec2_sleep()
    mgmt.start_vm(new_instance.name)
    if new_instance.provider.one_of(EC2Provider):
        ec2_sleep()


def count_events(target, vm):
    timelines_view = navigate_to(target, 'Timelines')
    timelines_view.filter.time_position.select_by_visible_text('centered')
    timelines_view.filter.apply.click()
    found_events = []
    for evt in timelines_view.chart.get_events():
        # BZ(1428797)
        if not hasattr(evt, 'source_instance'):
            logger.warn("event {evt!r} doesn't have source_vm field. "
                        "Probably issue".format(evt=evt))
            continue
        elif evt.source_instance == vm.name:
            found_events.append(evt)

    logger.info("found events: {evt}".format(evt="\n".join([repr(e) for e in found_events])))
    return len(found_events)


def test_cloud_provider_event(gen_events, new_instance):
    """ Tests provider events on timelines

    Metadata:
        test_flag: timelines, provision
    """
    wait_for(count_events, [new_instance.provider, new_instance], timeout='5m', fail_condition=0,
             message="events to appear")


def test_cloud_azone_event(gen_events, new_instance):
    """ Tests availability zone events on timelines

    Metadata:
        test_flag: timelines, provision
    """
    # obtaining this instance's azone
    zone_id = new_instance.get_vm_via_rest().availability_zone_id
    zones = new_instance.appliance.rest_api.collections.availability_zones
    zone_name = next(zone.name for zone in zones if zone.id == zone_id)
    azone = AvailabilityZone(name=zone_name, provider=new_instance.provider,
                             appliance=new_instance.appliance)
    wait_for(count_events, [azone, new_instance], timeout='5m', fail_condition=0,
             message="events to appear")


def test_cloud_instance_event(gen_events, new_instance):
    """ Tests vm events on timelines

    Metadata:
        test_flag: timelines, provision
    """
    wait_for(count_events, [new_instance, new_instance], timeout='5m', fail_condition=0,
             message="events to appear")


@pytest.mark.manual
def test_policy_events():
    pass
