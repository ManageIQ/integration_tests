"""Runs an appliance for a set period of time to collect a bunch of messages.  Post processes evm
log file aftwards and creates a bunch of graphs displaying the queued/execution time of the backend
messages.
"""
from cfme.configure.configuration import candu
from utils.conf import perf_tests
from utils.log import logger
from utils.path import log_path
from utils.perf import collect_log
from utils.perf_message_stats import perf_process_evm
import os
import os.path
import pytest
import subprocess
import time

pytestmark = [
    pytest.mark.meta(
        server_roles="+ems_metrics_coordinator +ems_metrics_collector +ems_metrics_processor")
]


@pytest.fixture(scope="module")
def enable_candu():
    candu.enable_all()


@pytest.mark.usefixtures("setup_infrastructure_providers")
def test_queue_infrastructure(request, ssh_client, enable_candu):
    local_evm_gz = str(log_path.join('evm.perf.log.gz'))
    local_evm = str(log_path.join('evm.perf.log'))
    local_top_gz = str(log_path.join('top_output.perf.log.gz'))
    local_top = str(log_path.join('top_output.perf.log'))

    def clean_up_log_files(files):
        for clean_file in files:
            # Clean up collected log files as they can be huge in case of exception
            if os.path.exists(clean_file):
                logger.info('Removing: %s', clean_file)
                os.remove(clean_file)
    request.addfinalizer(lambda: clean_up_log_files([local_evm, local_evm_gz, local_top,
        local_top_gz]))

    sleep_time = perf_tests['test_queue']['infra_time']

    logger.info('Waiting: %s', sleep_time)
    time.sleep(sleep_time)

    collect_log(ssh_client, 'evm', local_evm_gz)
    collect_log(ssh_client, 'top_output', local_top_gz, strip_whitespace=True)

    logger.info('Calling gunzip %s', local_evm_gz)
    subprocess.call(['gunzip', local_evm_gz])

    logger.info('Calling gunzip {}'.format(local_top_gz))
    subprocess.call(['gunzip', local_top_gz])

    # Post process evm log and top_output log for charts and csvs
    perf_process_evm(local_evm, local_top)
