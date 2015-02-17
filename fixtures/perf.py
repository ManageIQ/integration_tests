"""Fixtures specifically for performance tests."""
import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import (Form, Select, fill, form_buttons)
from utils.appliance import IPAppliance
from utils.browser import quit
from utils.log import logger
from utils.perf import get_benchmark_providers
from utils.perf import set_rails_loglevel
from utils.perf import get_worker_pid
from utils.ssh import SSHClient
from utils import providers
import pytest

connection_broker = Form(
    fields=[
        ('value', Select("select#vim_broker_worker_threshold"))
    ]
)


@pytest.fixture(scope='module')
def benchmark_providers():
    """Adds all benchmark providers to an appliance."""
    bench_providers = get_benchmark_providers()
    for provider in bench_providers:
        providers.setup_provider(provider, validate=False)


@pytest.yield_fixture(scope='session')
def cfme_log_level_rails_debug():
    """Sets the log level for rails to debug and back to info."""
    set_rails_loglevel('debug')
    yield
    set_rails_loglevel('info')


@pytest.fixture(scope='function')
def clean_appliance(wait_for_ui=True):
    """Cleans an appliance database back to original state"""
    logger.info("Cleaning appliance")
    ssh_client = SSHClient()
    exit_status, output = ssh_client.run_command('service evmserverd stop')
    exit_status, output = ssh_client.run_command('sync; sync; echo 3 > /proc/sys/vm/drop_caches')
    exit_status, output = ssh_client.run_command('service postgresql92-postgresql restart')
    ssh_client.run_rake_command('evm:db:reset')
    ssh_client.run_rake_command('db:seed')
    exit_status, output = ssh_client.run_command('service evmserverd start')
    if wait_for_ui:
        logger.info("Waiting for WebUI.")
        ipapp = IPAppliance()
        ipapp.wait_for_web_ui()
        quit()  # Closes browser out to avoid error with future UI navigation


@pytest.fixture(scope="function")
def clear_all_caches():
    """Clears appliance OS caches and clears postgres cache through postgres restart"""
    clear_os_caches()
    clear_postgres_cache()


@pytest.fixture(scope="function")
def clear_os_caches():
    """Clears appliance OS caches"""
    logger.info('Dropping OS caches...')
    ssh_client = SSHClient()
    exit_status, output = ssh_client.run_command('sync; sync; echo 3 > /proc/sys/vm/drop_caches')


@pytest.fixture(scope="function")
def clear_postgres_cache():
    """Clears postgres cache through postgres restart"""
    logger.info('Dropping Postgres cache...')
    ssh_client = SSHClient()
    exit_status, output = ssh_client.run_command('service postgresql92-postgresql restart')


@pytest.yield_fixture(scope='module')
def ui_worker_pid():
    yield get_worker_pid('MiqUiWorker')


@pytest.yield_fixture(scope='module')
def patch_broker_cache_scope():
    """Fixture for patching VimBrokerWorker's cache scope to cache_scope_ems_refresh regardless of
    whether Inventory role is enabled."""
    set_patch_broker_cache_scope(True)
    yield
    set_patch_broker_cache_scope(False)


@pytest.yield_fixture(scope='module')
def patch_rails_console_use_vim_broker():
    """Fixture for patching /var/www/miq/vmdb/app/models/ems_refresh.rb to allow using vim broker
    from rails console for refresh benchmark tests."""
    set_patch_rails_console_use_vim_broker(True)
    yield
    set_patch_rails_console_use_vim_broker(False)


@pytest.yield_fixture(scope="function")
def vim_broker_3_gb_threshold():
    set_vim_broker_memory_threshold('3 GB')
    yield
    set_vim_broker_memory_threshold()


def set_vim_broker_memory_threshold(memory_value='2 GB'):
    """Sets VIMBroker's Memory threshold"""
    sel.force_navigate("cfg_settings_currentserver_workers")
    fill(
        connection_broker,
        dict(value=memory_value),
        action=form_buttons.save
    )


def set_patch_rails_console_use_vim_broker(use_vim_broker):
    """Patches /var/www/miq/vmdb/app/models/ems_refresh.rb to allow using vim broker from rails
    console for refresh benchmark tests."""
    ems_refresh_file = '/var/www/miq/vmdb/app/models/ems_refresh.rb'
    ssh_client = SSHClient()
    if use_vim_broker:
        ssh_client.run_command('sed -i \'s/def self.init_console(use_vim_broker = false)/'
            'def self.init_console(use_vim_broker = true)/g\' {}'.format(ems_refresh_file))
    else:
        ssh_client.run_command('sed -i \'s/def self.init_console(use_vim_broker = true)/'
            'def self.init_console(use_vim_broker = false)/g\' {}'.format(ems_refresh_file))


def set_patch_broker_cache_scope(cache_scope_ems_refresh):
    """Patches VimBrokerWorker cache scope to cache_scope_ems_refresh regardless of whether
    Inventory role is enabled."""
    vim_broker_file = '/var/www/miq/vmdb/lib/workers/vim_broker_worker.rb'
    ssh_client = SSHClient()
    if cache_scope_ems_refresh:
        ssh_client.run_command('sed -i \'s/@active_roles.include?("ems_inventory") ?'
            ' :cache_scope_ems_refresh : :cache_scope_core/@active_roles.include?("ems_inventory")'
            ' ? :cache_scope_ems_refresh : :cache_scope_ems_refresh/g\' {}'.format(vim_broker_file))
    else:
        ssh_client.run_command('sed -i \'s/@active_roles.include?("ems_inventory") ?'
            ' :cache_scope_ems_refresh : :cache_scope_ems_refresh/'
            '@active_roles.include?("ems_inventory") ? :cache_scope_ems_refresh :'
            ' :cache_scope_core/g\' {}'.format(vim_broker_file))
    # No need to restart evm service as this is performed before an appliance is cleaned.
    # ipapp = IPAppliance()
    # ipapp.restart_evm_service()
    # ipapp.wait_for_web_ui()
    # quit()  # Closes browser out to avoid error with future UI navigation
