"""Runs an appliance for a set period of time to collect a bunch of messages.  Post processes evm
log file aftwards and creates a bunch of graphs displaying the queued/execution time of the backend
messages.
"""
from cfme.configure.configuration import candu
from utils.perf_message_stats import perf_process_evm
from utils.conf import perf_tests
from utils.log import logger
from utils.path import log_path, scripts_path
import pytest
import subprocess
import time
import os
import os.path

pytestmark = [
    pytest.mark.meta(
        server_roles="+ems_metrics_coordinator +ems_metrics_collector +ems_metrics_processor")
]


@pytest.fixture(scope="module")
def enable_candu():
    candu.enable_all()


@pytest.mark.usefixtures("setup_infrastructure_providers")
def test_queue_infrastructure(ssh_client, enable_candu):
    local_evm_gz = str(log_path.join('evm.perf.log.gz'))
    local_evm = str(log_path.join('evm.perf.log'))

    ssh_client.put_file(str(scripts_path.join('perf_collect_logs.sh')),
        '/root/perf_collect_logs.sh')

    sleep_time = perf_tests['test_queue']['infra_time']

    logger.info('Waiting: {}'.format(sleep_time))
    time.sleep(sleep_time)

    # Collect evm log for post process
    ssh_client.run_command('./perf_collect_logs.sh /var/www/miq/vmdb/log/ evm')

    # Ensure there is not a conflicting local evm log file
    if os.path.exists(local_evm):
        logger.info('Cleaning up evm.perf.log before getting file: {}'.format(local_evm_gz))
        os.remove(local_evm)

    ssh_client.get_file('/var/www/miq/vmdb/log/evm.perf.log.gz', local_evm_gz)

    # Clean up the evm.perf.log.gz file on the appliance
    ssh_client.run_command('rm -f /var/www/miq/vmdb/log/evm.perf.log.gz')

    # Uncompress the evm log file evm.perf.log.gz
    logger.info('Calling gunzip {}'.format(local_evm_gz))
    subprocess.call(['gunzip', local_evm_gz])

    # Post process evm log for queue metrics and produce graphs, and csvs
    perf_process_evm(local_evm)

    # Clean up and delete evm.perf.log as it is likely huge...
    if os.path.exists(local_evm):
        logger.info('Removing: {}'.format(local_evm))
        os.remove(local_evm)
