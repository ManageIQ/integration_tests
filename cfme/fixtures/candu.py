"""
Fixtures for Capacity and Utilization
"""
import fauxfactory
import pytest

from cfme.utils import conf
from cfme.utils.ssh import SSHClient


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
    tag = enable_candu_category.collections.tags.instantiate(name="london", display_name="London")
    vm.add_tag(tag, exists_check=True)
    return vm


@pytest.fixture(scope="module")
def candu_db_restore(request, temp_appliance_extended_db):
    app = temp_appliance_extended_db
    # get DB backup file
    db_storage_hostname = conf.cfme_data.bottlenecks.hostname
    db_storage_ssh = SSHClient(hostname=db_storage_hostname, **conf.credentials.bottlenecks)
    file_name = getattr(request, 'param', 'candu.db.backup')
    rand_filename = f"/tmp/db.backup_{fauxfactory.gen_alphanumeric()}"
    db_storage_ssh.get_file(
        f"{conf.cfme_data.bottlenecks.backup_path}/{file_name}",
        rand_filename
    )
    app.ssh_client.put_file(rand_filename, "/tmp/evm_db.backup")

    app.evmserverd.stop()
    app.db.drop()
    app.db.create()
    app.db.restore()
    # When you load a database from an older version of the application, you always need to
    # run migrations.
    # https://bugzilla.redhat.com/show_bug.cgi?id=1643250
    app.db.migrate()
    app.db.fix_auth_key()
    app.db.fix_auth_dbyml()
    app.evmserverd.start()
    app.wait_for_miq_ready()


@pytest.fixture(params=["regions", "providers", "clusters", "hosts"])
def entity_init(temp_appliance_extended_db, request, provider):
    appliance = temp_appliance_extended_db
    provider.appliance = appliance
    if request.param == "regions":
        return appliance.collections.regions.instantiate(appliance.region()[-1])
    if request.param == "providers":
        return provider
    if request.param == "clusters":
        return appliance.collections.clusters.instantiate(name=provider.data["clusters"][0],
        provider=provider)
    if request.param == "hosts":
        return appliance.collections.hosts.instantiate(name=provider.data["hosts"][0].name,
        provider=provider)
