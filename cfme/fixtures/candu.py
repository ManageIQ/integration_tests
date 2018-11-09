"""
Fixtures for Capacity and Utilization
"""
import pytest


@pytest.fixture(scope="module")
def enable_candu(appliance):
    candu = appliance.collections.candus
    server_settings = appliance.server.settings
    original_roles = server_settings.server_roles_db

    server_settings.enable_server_roles(
        'ems_metrics_coordinator',
        'ems_metrics_collector',
        'ems_metrics_processor'
    )
    server_settings.disable_server_roles(
        'automate',
        'smartstate'
    )
    candu.enable_all()

    yield

    candu.disable_all()
    server_settings.update_server_roles_db(original_roles)


@pytest.fixture(scope="module")
def collect_data(appliance, provider, interval='hourly', back='7.days'):
    """Collect hourly back data for vsphere provider"""
    vm_name = provider.data['cap_and_util']['chargeback_vm']

    # Capture real-time C&U data
    ret = appliance.ssh_client.run_rails_command(
        "\"vm = Vm.where(:ems_id => {}).where(:name => {})[0];\
        vm.perf_capture({}, {}.ago.utc, Time.now.utc)\""
        .format(provider.id, repr(vm_name), repr(interval), back))
    return ret.success


@pytest.fixture(scope="module")
def enable_candu_category(appliance):
    """Enable capture C&U Data for tag category location by navigating to the Configuration ->
       Region page. Click 'Tags' tab , select required company category under
       'My Company Categories' and enable 'Capture C & U Data' for the category.
    """
    collection = appliance.collections.categories
    location_category = collection.instantiate(name="location", display_name="Location")
    if not location_category.capture_candu:
        location_category.update(updates={"capture_candu": True})
    return location_category


@pytest.fixture(scope="function")
def candu_tag_vm(provider, enable_candu_category):
    """Add location tag to VM if not available"""
    collection = provider.appliance.provider_based_collection(provider)
    vm = collection.instantiate('cu-24x7', provider)
    if not vm.exists:
        pytest.skip(
            "{vm_name} Utilization VM not exist on {prov}".format(
                vm_name=vm.name, prov=provider.name
            )
        )

    available_tags = vm.get_tags()
    tag = enable_candu_category.collections.tags.instantiate(name="london", display_name="London")

    if tag.display_name not in [item.display_name for item in available_tags]:
        vm.add_tag(tag)
    return vm
