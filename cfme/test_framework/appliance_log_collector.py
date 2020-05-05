"""Plugin for collection of appliance logs

Options in env.yaml will define what files to collect, will default to the set below

.. code-block::yaml
    log_collector:
        local_dir: log/appliance/  # Local to log_path
        log_files:
            - /var/www/miq/vmdb/log/evm.log
            - /var/www/miq/vmdb/log/production.log
            - /var/www/miq/vmdb/log/automation.log
            - /var/www/miq/vmdb/log/appliance_console.log

Log files will be tarred and written to log_path
"""
import pytest

from cfme.utils.conf import env
from cfme.utils.log import logger
from cfme.utils.path import log_path


DEFAULT_FILES = ['/var/www/miq/vmdb/log/evm.log',
                 '/var/www/miq/vmdb/log/production.log',
                 '/var/www/miq/vmdb/log/automation.log',
                 '/var/www/miq/vmdb/log/appliance_console.log']

DEFAULT_LOCAL = log_path


def pytest_addoption(parser):
    parser.addoption('--collect-logs', action='store_true',
                     help=("Collect logs from all appliances and store locally at session "
                           "shutdown. Configured via log_collector in env.yaml."))


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_unconfigure(config):
    yield  # since hookwrapper, let hookimpl run
    if config.getoption('--collect-logs'):
        logger.info("Starting log collection on appliances.")
        log_files = DEFAULT_FILES
        local_dir = DEFAULT_LOCAL
        try:
            log_files = env.log_collector.log_files
        except (AttributeError, KeyError):
            logger.info("No log_collector.log_files in env, using the default: %s", log_files)
            pass
        try:
            local_dir = log_path.join(env.log_collector.local_dir)
        except (AttributeError, KeyError):
            logger.info("No log_collector.local_dir in env, using the default: %s", local_dir)
            pass

        # Handle local dir existing
        local_dir.ensure(dir=True)
        from cfme.test_framework.appliance import PLUGIN_KEY
        holder = config.pluginmanager.get_plugin(PLUGIN_KEY)
        if holder is None:
            # No appliances to fetch logs from
            logger.warning("No logs collected, appliance holder is empty.")
            return

        written_files = []
        for app in holder.pool:
            with app.ssh_client as ssh_client:
                tar_file = f'log-collector-{app.hostname}.tar.gz'
                logger.debug(f"Creating tar file on appliance {app}:{tar_file} "
                    f"with log files {' '.join(log_files)}")
                # wrap the files in ls, redirecting stderr, to ignore files that don't exist
                tar_result = ssh_client.run_command(
                    f"tar -czvf {tar_file} $(ls {' '.join(log_files)} 2>/dev/null)")
                try:
                    assert tar_result.success
                except AssertionError:
                    logger.exception("tar command non-zero RC when collecting logs on "
                        f"{app}: {tar_result.output}")
                    continue
                ssh_client.get_file(tar_file, local_dir.strpath)
            written_files.append(tar_file)
        logger.info("Wrote the following files to local log path: %s", written_files)
