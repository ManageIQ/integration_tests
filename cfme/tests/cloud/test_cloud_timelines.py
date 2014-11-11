import pytest
from cfme.cloud.instance import instance_factory, details_page
from cfme.cloud.provider import prov_timeline
from cfme.web_ui import toolbar
from utils import testgen
from utils.log import logger
from utils.providers import setup_provider
from utils.randomness import generate_random_string

bz1127960 = pytest.mark.bugzilla(
    1127960, unskip={1127960: lambda appliance_version: appliance_version >= "5.3"})

pytestmark = [pytest.mark.usefixtures('setup_providers')]


def pytest_generate_tests(metafunc):
    # Filter out EC2 since EC2 doesn't support timelines
    argnames, argvalues, idlist = testgen.provider_by_type(metafunc,
        provider_types=['openstack'])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


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
def setup_providers(provider_key):
    # Normally function-scoped
    setup_provider(provider_key)


@pytest.fixture(scope="module")
def vm_name():
    return "test_instance_timeline_{}".format(generate_random_string())


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
def test_instance(request, delete_instances_fin, provider_crud, provider_mgmt, vm_name):
    """ Fixture to provision instance on the provider
    """
    instance = instance_factory(vm_name, provider_crud)
    if not provider_mgmt.does_vm_exist(vm_name):
        delete_instances_fin[provider_crud.key] = instance
        instance.create_on_provider()
    return instance


@pytest.fixture(scope="module")
def gen_events(delete_fx_provider_event, provider_crud, test_instance):
    logger.debug('Starting, stopping VM')
    mgmt = provider_crud.get_mgmt_system()
    mgmt.stop_vm(test_instance.name)
    mgmt.start_vm(test_instance.name)
    provider_crud.refresh_provider_relationships()


@pytest.mark.bugzilla(1127960)
def test_provider_event(provider_crud, gen_events, test_instance):
    pytest.sel.force_navigate('cloud_provider_timelines',
                              context={'provider': provider_crud})
    events = []
    for event in prov_timeline.events():
        data = event.block_info()
        if test_instance.name in data.values():
            events.append(event)
            assert(len(events) > 0)
            break


@pytest.mark.bugzilla(1127960)
def test_azone_event(provider_crud, gen_events, test_instance):
    test_instance.load_details()
    pytest.sel.click(details_page.infoblock.element('Relationships', 'Availability Zone'))
    toolbar.select('Monitoring', 'Timelines')
    events = []
    for event in prov_timeline.events():
        data = event.block_info()
        if test_instance.name in data.values():
            events.append(event)
            assert(len(events) > 0)
            break


@pytest.mark.bugzilla(1127960)
def test_vm_event(provider_crud, gen_events, test_instance):
    test_instance.load_details()
    toolbar.select('Monitoring', 'Timelines')
    events = []
    for event in prov_timeline.events():
        data = event.block_info()
        if test_instance.name in data.values():
            events.append(event)
            assert(len(events) > 0)
            break
