"""Runs discovery benchmarks."""
from utils.conf import cfme_data
from utils.conf import perf_tests
from utils.log import logger
from utils.perf import get_benchmark_providers
from utils.perf import log_stats
from utils.perf import set_server_roles_benchmark
import pytest

pytestmark = [
    pytest.mark.parametrize('provider', get_benchmark_providers())
]


def test_discovery_provider(ssh_client, clean_appliance, provider):
    """Measures time required to discover a provider."""
    set_server_roles_benchmark()
    reps = perf_tests['feature']['discovery']['provider']
    ip_addr = cfme_data['management_systems'][provider]['ipaddress']
    discover_type = ':{}'.format(cfme_data['management_systems'][provider]['type'])
    command = ('Benchmark.realtime { Host.discoverHost(Marshal.dump({:ipaddr => '
               '\'' + str(ip_addr) + '\', :discover_types => [' + str(discover_type) + '],'
               ' :timeout => 10 }))}')
    timings = []
    for repetition in range(1, reps + 1):
        exit_status, output = ssh_client.run_rails_console(command, sandbox=True, timeout=None)
        timings.append(float(output.strip().split('\n')[-1]))
        logger.info('Repetition: {}, Value: {}'.format(repetition, output.strip().split('\n')[-1]))
    log_stats(timings, 'Discovery', 'Provider', cfme_data['management_systems'][provider]['name'])
