"""Runs refresh benchmarks with the vim broker worker cache."""
from utils.conf import cfme_data
from utils.conf import perf_tests
from utils.log import logger
from utils.perf import append_timing
from utils.perf import get_benchmark_vmware_providers
from utils.perf import log_stats
from utils.perf import set_full_refresh_threshold
from utils.perf import set_server_roles_benchmark
from utils.perf import wait_for_vim_broker
from utils import providers
import pytest

pytestmark = [
    pytest.mark.usefixtures('patch_rails_console_use_vim_broker', 'patch_broker_cache_scope',
        'end_log_stats')
]

b_timings = {}


@pytest.yield_fixture(scope='session')
def end_log_stats():
    yield
    logger.info('logging Timings: {}'.format(b_timings))
    for test in sorted(b_timings.keys()):
        for subtest in sorted(b_timings[test].keys()):
            for provider in sorted(b_timings[test][subtest].keys()):
                log_stats(b_timings[test][subtest][provider], test, subtest, provider)


@pytest.mark.parametrize('repetition', range(0, perf_tests['feature']['refresh']['provider_init']))
@pytest.mark.parametrize('provider', get_benchmark_vmware_providers())
def test_refresh_broker_provider_init(ssh_client, clean_appliance, repetition, provider):
    """Measures time required to complete an initial EmsRefresh.refresh on specific provider."""
    set_server_roles_benchmark()
    provider_name = cfme_data['management_systems'][provider]['name']
    providers.setup_provider(provider, validate=False)
    wait_for_vim_broker()
    command = ('e = ExtManagementSystem.find_by_name(\'' + provider_name + '\');'
               'Benchmark.realtime {EmsRefresh.refresh e}')
    exit_status, output = ssh_client.run_rails_console(command, timeout=None)
    append_timing(b_timings, 'Refresh', 'Provider-Broker-Init', provider_name,
        float(output.strip().split('\n')[-1]))
    logger.info('Repetition: {}, Value: {}'.format(repetition, output.strip().split('\n')[-1]))


@pytest.mark.parametrize('repetition', range(0, perf_tests['feature']['refresh']['provider_init']))
@pytest.mark.parametrize('provider', get_benchmark_vmware_providers())
def test_refresh_broker_provider_init_profile_perftools(ssh_client, clean_appliance, repetition,
        provider):
    """Measures time required to complete an initial EmsRefresh.refresh on specific provider and
    profile using perftools.rb.  Appliance must be setup with perftools in advance.  Profile file
    is saved to appliance /root directory.  The file is unique between repetitions but not runs of
    the automation currently.
    Works with Ruby 1.9.3/2.0.0 w/ perftools.rb
    """
    set_server_roles_benchmark()
    provider_name = cfme_data['management_systems'][provider]['name']
    providers.setup_provider(provider, validate=False)
    wait_for_vim_broker()
    command = ('require \'perftools\';'
               'e = ExtManagementSystem.find_by_name(\'' + provider_name + '\');'
               'GC.start;'
               'PerfTools::CpuProfiler.start(\'/root/perftools-provider-init-broker-'
                + provider_name + '-' + str(repetition) + '\');'
               'value = Benchmark.realtime {EmsRefresh.refresh e};'
               'PerfTools::CpuProfiler.stop;'
               'value')
    exit_status, output = ssh_client.run_rails_console(command, timeout=None)
    append_timing(b_timings, 'Refresh', 'Provider-Broker-Init-Perftools', provider_name,
        float(output.strip().split('\n')[-1]))
    logger.info('Repetition: {}, Value: {}'.format(repetition, output.strip().split('\n')[-1]))


@pytest.mark.parametrize('repetition', range(0, perf_tests['feature']['refresh']['provider_init']))
@pytest.mark.parametrize('provider', get_benchmark_vmware_providers())
def test_refresh_broker_provider_init_profile_stackprof(ssh_client, clean_appliance, repetition,
        provider):
    """Measures time required to complete an initial EmsRefresh.refresh on specific provider and
    profile using perftools.rb.  Appliance must be setup with stackprof in advance.  Profile file
    is saved to appliance /root directory.  The file is unique between repetitions but not runs of
    the automation currently.
    Works with Ruby 2.1.x w/ stackprof
    """
    set_server_roles_benchmark()
    provider_name = cfme_data['management_systems'][provider]['name']
    providers.setup_provider(provider, validate=False)
    wait_for_vim_broker()
    command = ('e = ExtManagementSystem.find_by_name(\'' + provider_name + '\');'
               'GC.start;'
               'value = 0;'
               'StackProf.run(mode: :cpu, out: \'/root/stackprof-provider-init-broker-'
                + provider_name + '-' + str(repetition) + '\') do;'
               'value = Benchmark.realtime {EmsRefresh.refresh e};'
               'end;'
               'value')
    exit_status, output = ssh_client.run_rails_console(command, timeout=None)
    append_timing(b_timings, 'Refresh', 'Provider-Broker-Init-Stackprof', provider_name,
        float(output.strip().split('\n')[-1]))
    logger.info('Repetition: {}, Value: {}'.format(repetition, output.strip().split('\n')[-1]))


@pytest.mark.parametrize('provider', get_benchmark_vmware_providers())
def test_refresh_broker_provider_delta(ssh_client, clean_appliance, provider):
    """Measures time required to complete an EmsRefresh.refresh on specific provider after initial
    refresh.
    """
    set_server_roles_benchmark()
    reps = perf_tests['feature']['refresh']['provider_nc']
    provider_name = cfme_data['management_systems'][provider]['name']
    providers.setup_provider(provider, validate=False)
    wait_for_vim_broker()
    command = ('e = ExtManagementSystem.find_by_name(\'' + provider_name + '\');'
               'EmsRefresh.refresh e;'
               'r = Array.new;'
               '' + str(reps) + '.times {|i| r.push(Benchmark.realtime{EmsRefresh.refresh e})};'
               'r')

    exit_status, output = ssh_client.run_rails_console(command, timeout=None)
    output_line = output.strip().split('\n')[-1]
    output_line = output_line.replace(']', '').replace('[', '')
    timings = [float(timing) for timing in output_line.split(',')]
    log_stats(timings, 'Refresh', 'Provider-Broker-Delta', provider_name)


@pytest.mark.parametrize('provider', get_benchmark_vmware_providers())
def test_refresh_broker_provider_delta_profile_perftools(ssh_client, clean_appliance, provider):
    """Measures time required to complete an EmsRefresh.refresh on specific provider after initial
    refresh.
    Works with Ruby 1.9.3/2.0.0 w/ perftools.rb
    """
    set_server_roles_benchmark()
    reps = perf_tests['feature']['refresh']['provider_nc']
    provider_name = cfme_data['management_systems'][provider]['name']
    providers.setup_provider(provider, validate=False)
    wait_for_vim_broker()
    command = ('require \'perftools\';'
               'e = ExtManagementSystem.find_by_name(\'' + provider_name + '\');'
               'EmsRefresh.refresh e;'
               'r = Array.new;'
               'GC.start;'
               'PerfTools::CpuProfiler.start(\'/root/perftools-provider-delta-broker-'
                + provider_name + '\');'
               'r.push(Benchmark.realtime {EmsRefresh.refresh e});'
               'PerfTools::CpuProfiler.stop;'
               'r')
    exit_status, output = ssh_client.run_rails_console(command, timeout=None)
    output_line = output.strip().split('\n')[-1]
    output_line = output_line.replace(']', '').replace('[', '')
    timings = [float(timing) for timing in output_line.split(',')]
    log_stats(timings, 'Refresh', 'Provider-Broker-Delta-Perftools', provider_name)


@pytest.mark.parametrize('provider', get_benchmark_vmware_providers())
def test_refresh_broker_provider_delta_profile_stackprof(ssh_client, clean_appliance, provider):
    """Measures time required to complete an EmsRefresh.refresh on specific provider after initial
    refresh.
    Works with Ruby 2.1.x w/ stackprof
    """
    set_server_roles_benchmark()
    reps = perf_tests['feature']['refresh']['provider_nc']
    provider_name = cfme_data['management_systems'][provider]['name']
    providers.setup_provider(provider, validate=False)
    wait_for_vim_broker()
    command = ('e = ExtManagementSystem.find_by_name(\'' + provider_name + '\');'
               'EmsRefresh.refresh e;'
               'r = Array.new;'
               'GC.start;'
               'StackProf.run(mode: :cpu, out: \'/root/stackprof-provider-delta-broker-'
                + provider_name + '\') do;'
               'r.push(Benchmark.realtime {EmsRefresh.refresh e});'
               'end;'
               'r')
    exit_status, output = ssh_client.run_rails_console(command, timeout=None)
    output_line = output.strip().split('\n')[-1]
    output_line = output_line.replace(']', '').replace('[', '')
    timings = [float(timing) for timing in output_line.split(',')]
    log_stats(timings, 'Refresh', 'Provider-Broker-Delta-Stackprof', provider_name)


@pytest.mark.parametrize('provider', get_benchmark_vmware_providers())
def test_refresh_broker_host(ssh_client, clean_appliance, provider):
    """Measures time required to complete an EmsRefresh.refresh on specific host after initial
    refresh.
    """
    set_server_roles_benchmark()
    reps = perf_tests['feature']['refresh']['host']
    provider_name = cfme_data['management_systems'][provider]['name']
    providers.setup_provider(provider, validate=False)
    wait_for_vim_broker()
    command = ('e = ExtManagementSystem.find_by_name(\'' + provider_name + '\');'
               'EmsRefresh.refresh e;'
               'h = Host.find(:all);'
               'r = Array.new;'
               '' + str(reps) + '.times {|i| r.push(Benchmark.realtime{EmsRefresh.refresh h[0]})};'
               'r')
    exit_status, output = ssh_client.run_rails_console(command, timeout=None)
    output_line = output.strip().split('\n')[-1]
    output_line = output_line.replace(']', '').replace('[', '')
    timings = [float(timing) for timing in output_line.split(',')]
    log_stats(timings, 'Refresh', 'Host-Broker', provider_name)


@pytest.mark.parametrize('provider', get_benchmark_vmware_providers())
@pytest.mark.parametrize('num_vms', [1, 25, 50, 75, 100])
def test_refresh_broker_vm(ssh_client, clean_appliance, provider, num_vms):
    """Measures time required to complete an EmsRefresh.refresh on specific VM(s) after initial
    refresh.
    """
    set_server_roles_benchmark()
    reps = perf_tests['feature']['refresh']['vm']
    provider_name = cfme_data['management_systems'][provider]['name']
    providers.setup_provider(provider, validate=False)
    wait_for_vim_broker()
    refresh_target = 'EmsRefresh.refresh v[0..{}]'.format(num_vms - 1)
    if num_vms >= 100:
        set_full_refresh_threshold(num_vms + 1)
    command = ('e = ExtManagementSystem.find_by_name(\'' + provider_name + '\');'
               'EmsRefresh.refresh e;'
               'v = VmInfra.find(:all);'
               'r = Array.new;'
               '' + str(reps) + '.times {|i| r.push(Benchmark.realtime{ ' + refresh_target + ' })};'
               'r')
    exit_status, output = ssh_client.run_rails_console(command, timeout=None)
    output_line = output.strip().split('\n')[-1]
    output_line = output_line.replace(']', '').replace('[', '')
    timings = [float(timing) for timing in output_line.split(',')]
    log_stats(timings, 'Refresh', 'VM-Broker-{}'.format(num_vms), provider_name)
    if num_vms >= 100:
        set_full_refresh_threshold()
