# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from cfme.cloud.instance import Instance
from cfme.web_ui import InfoBlock, toolbar, jstimelines
from cfme.exceptions import ToolbarOptionGreyedOrUnavailable
from utils import testgen
from utils import version
from utils.blockers import BZ
from utils.log import logger
from utils.wait import wait_for


pytest_generate_tests = testgen.generate(testgen.cloud_providers, scope="module")

pytestmark = [pytest.mark.tier(2)]


@pytest.fixture(scope="module")
def delete_fx_provider_event(db, provider):
    logger.info("Deleting timeline events for provider name %s", provider.name)
    ems = db['ext_management_systems']
    ems_events_table_name = version.pick({version.LOWEST: 'ems_events', '5.5': 'event_streams'})
    ems_events = db[ems_events_table_name]
    with db.transaction:
        providers = (
            db.session.query(ems_events.id)
            .join(ems, ems_events.ems_id == ems.id)
            .filter(ems.name == provider.name)
        )
        db.session.query(ems_events).filter(ems_events.id.in_(providers.subquery())).delete(False)


@pytest.fixture(scope="module")
def vm_name():
    # We have to use "tt" here to avoid name truncating in the timelines view
    return "test_tt_{}".format(fauxfactory.gen_alphanumeric())


@pytest.fixture(scope="module")
def delete_instances_fin(request):
    """ Fixture to add a finalizer to delete provisioned instances at the end of tests

    This is a "trashbin" fixture - it returns a mutable that you put stuff into.
    """
    provisioned_instances = {}

    def delete_instances(instances_dict):
        for instance in instances_dict.itervalues():
            instance.delete_from_provider()
    request.addfinalizer(lambda: delete_instances(provisioned_instances))
    return provisioned_instances


@pytest.fixture(scope="module")
def test_instance(setup_provider_modscope, request, delete_instances_fin, provider, vm_name):
    """ Fixture to provision instance on the provider
    """
    instance = Instance.factory(vm_name, provider)
    if not provider.mgmt.does_vm_exist(vm_name):
        delete_instances_fin[provider.key] = instance
        instance.create_on_provider(allow_skip="default")
    return instance


@pytest.fixture(scope="module")
def gen_events(setup_provider_modscope, delete_fx_provider_event, provider, test_instance):
    logger.debug('Starting, stopping VM')
    mgmt = provider.mgmt
    mgmt.stop_vm(test_instance.name)
    mgmt.start_vm(test_instance.name)
    provider.refresh_provider_relationships()


def count_events(instance_name, nav_step):
    try:
        nav_step()
    except ToolbarOptionGreyedOrUnavailable:
        return 0
    events = []
    for event in jstimelines.events():
        data = event.block_info()
        if instance_name in data.values():
            events.append(event)
            if len(events) > 0:
                return len(events)
    return 0


def db_event(db, provider):
    # Get event count from the DB
    logger.info("Getting event count from the DB for provider name %s", provider.name)
    ems = db['ext_management_systems']
    ems_events = db['event_streams']
    with db.transaction:
        providers = (
            db.session.query(ems_events.id)
            .join(ems, ems_events.ems_id == ems.id)
            .filter(ems.name == provider.name)
        )
        query = db.session.query(ems_events).filter(ems_events.id.in_(providers.subquery()))
        event_count = query.count()
    return event_count


@pytest.mark.meta(blockers=[BZ(1201923, unblock=lambda provider: provider.type != 'ec2',
                               forced_streams=['5.6']),
                            BZ(1390572, unblock=lambda provider: provider.type != 'azure',
                               forced_streams=['5.6'])])
def test_provider_event(setup_provider, provider, gen_events, test_instance):
    """ Tests provider events on timelines

    Metadata:
        test_flag: timelines, provision
    """
    def nav_step():
        pytest.sel.force_navigate('cloud_provider_timelines',
                                  context={'provider': provider})
    wait_for(count_events, [test_instance.name, nav_step], timeout=60, fail_condition=0,
             message="events to appear")


@pytest.mark.meta(blockers=[BZ(1201923, unblock=lambda provider: provider.type != 'ec2',
                               forced_streams=['5.6']),
                            BZ(1390572, unblock=lambda provider: provider.type != 'azure',
                               forced_streams=['5.6'])])
def test_azone_event(setup_provider, provider, gen_events, test_instance):
    """ Tests availablility zone events on timelines

    Metadata:
        test_flag: timelines, provision
    """
    def nav_step():
        test_instance.load_details()
        pytest.sel.click(InfoBlock.element('Relationships', 'Availability Zone'))
        toolbar.select('Monitoring', 'Timelines')
    wait_for(count_events, [test_instance.name, nav_step], timeout=60, fail_condition=0,
             message="events to appear")


@pytest.mark.meta(blockers=[BZ(1201923, unblock=lambda provider: provider.type != 'ec2',
                               forced_streams=['5.6']),
                            BZ(1390572, unblock=lambda provider: provider.type != 'azure',
                               forced_streams=['5.6'])])
def test_vm_event(setup_provider, provider, db, gen_events, test_instance, bug):
    """ Tests vm events on timelines

    Metadata:
        test_flag: timelines, provision
    """
    def nav_step():
        test_instance.load_details()
        toolbar.select('Monitoring', 'Timelines')

    wait_for(count_events, [test_instance.name, nav_step], timeout=60, fail_condition=0,
         message="events to appear")

    wait_for(db_event, [db, provider], num_sec=840, delay=30, fail_condition=0,
        message="events to appear in the DB")
