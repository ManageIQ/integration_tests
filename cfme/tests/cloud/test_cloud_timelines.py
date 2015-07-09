# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from cfme.cloud.instance import instance_factory, details_page
from cfme.web_ui import toolbar, jstimelines
from cfme.exceptions import ToolbarOptionGreyed
from utils import testgen, version
from utils.blockers import BZ
from utils.log import logger
from utils.wait import wait_for

pytestmark = [pytest.mark.ignore_stream("5.2")]
# bz1127960 = pytest.mark.bugzilla(
#    1127960, unskip={1127960: lambda appliance_version: appliance_version >= "5.3"})


pytest_generate_tests = testgen.generate(testgen.cloud_providers, scope="module")


@pytest.fixture(scope="module")
def delete_fx_provider_event(db, provider_crud):
    logger.debug("Deleting timeline events for provider name {}".format(provider_crud.name))
    ems = db['ext_management_systems']
    ems_events = db['ems_events']
    with db.transaction:
        providers = (
            db.session.query(ems_events.id)
            .join(ems, ems_events.ems_id == ems.id)
            .filter(ems.name == provider_crud.name)
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
def test_instance(setup_provider, request, delete_instances_fin, provider_crud,
                  provider_mgmt, vm_name):
    """ Fixture to provision instance on the provider
    """
    instance = instance_factory(vm_name, provider_crud)
    if not provider_mgmt.does_vm_exist(vm_name):
        delete_instances_fin[provider_crud.key] = instance
        instance.create_on_provider(allow_skip="default")
    return instance


@pytest.fixture(scope="module")
def gen_events(setup_provider, delete_fx_provider_event, provider_crud, test_instance):
    logger.debug('Starting, stopping VM')
    mgmt = provider_crud.get_mgmt_system()
    mgmt.stop_vm(test_instance.name)
    mgmt.start_vm(test_instance.name)
    provider_crud.refresh_provider_relationships()


def count_events(instance_name, nav_step):
    try:
        nav_step()
    except ToolbarOptionGreyed:
        return 0
    events = []
    for event in jstimelines.events():
        data = event.block_info()
        if instance_name in data.values():
            events.append(event)
            if len(events) > 0:
                return len(events)
    return 0


def db_event(db, provider_crud):
    # Get event count from the DB
    ems = db['ext_management_systems']
    ems_events = db['ems_events']
    with db.transaction:
        providers = (
            db.session.query(ems_events.id)
            .join(ems, ems_events.ems_id == ems.id)
            .filter(ems.name == provider_crud.name)
        )
        query = db.session.query(ems_events).filter(ems_events.id.in_(providers.subquery()))
        event_count = query.count()
    return event_count


@pytest.mark.meta(
    blockers=BZ(1201923, unblock=lambda provider_type: provider_type != 'ec2'),
)
@pytest.mark.uncollectif(
    lambda provider_type: version.current_version < "5.4" and provider_type == 'ec2')
def test_provider_event(setup_provider, provider_crud, provider_type, gen_events, test_instance):
    """ Tests provider events on timelines

    Metadata:
        test_flag: timelines, provision
    """
    def nav_step():
        pytest.sel.force_navigate('cloud_provider_timelines',
                                  context={'provider': provider_crud})
    wait_for(count_events, [test_instance.name, nav_step], timeout=60, fail_condition=0,
             message="events to appear")


@pytest.mark.meta(
    blockers=BZ(1201923, unblock=lambda provider_type: provider_type != 'ec2'),
)
@pytest.mark.uncollectif(
    lambda provider_type: version.current_version < "5.4" and provider_type == 'ec2')
def test_azone_event(setup_provider, provider_crud, provider_type, gen_events, test_instance):
    """ Tests availablility zone events on timelines

    Metadata:
        test_flag: timelines, provision
    """
    def nav_step():
        test_instance.load_details()
        pytest.sel.click(details_page.infoblock.element('Relationships', 'Availability Zone'))
        toolbar.select('Monitoring', 'Timelines')
    wait_for(count_events, [test_instance.name, nav_step], timeout=60, fail_condition=0,
             message="events to appear")


@pytest.mark.uncollectif(
    lambda provider_type: version.current_version < "5.4" and provider_type == 'ec2')
def test_vm_event(setup_provider, provider_crud, provider_type, db,
                 bug):
    """ Tests vm events on timelines

    Metadata:
        test_flag: timelines, provision
    """
    def nav_step():
        test_instance.load_details()
        toolbar.select('Monitoring', 'Timelines')

    ec2_bug = bug(1201923)
    if (ec2_bug is None or provider_type == 'openstack'):
        wait_for(count_events, [test_instance.name, nav_step], timeout=60, fail_condition=0,
             message="events to appear")

    wait_for(db_event, [db, provider_crud], num_sec=840, delay=30, fail_condition=0,
        message="events to appear in the DB")
