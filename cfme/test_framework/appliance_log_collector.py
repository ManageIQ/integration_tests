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
import os.path
import shutil
import subprocess

import pytest
import scp

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
                     help=('Collect logs from all appliances and store locally at session '
                           'shutdown.  Configured via log_collector in env.yaml'))


def pytest_addhooks(pluginmanager):
    """ This example assumes the hooks are grouped in the 'hooks' module. """
    pluginmanager.add_hookspecs(CollectLogsHookSpecs)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_unconfigure(config):
    yield  # since hookwrapper, let hookimpl run
    from cfme.test_framework.appliance import PLUGIN_KEY
    holder = config.pluginmanager.get_plugin(PLUGIN_KEY)
    if holder is None:
        # No appliances to fetch logs from
        logger.warning('No logs to collect, appliance holder is empty')
        return

    collect_logs = config.pluginmanager.hook.pytest_collect_logs
    collect_logs(config=config, appliances=holder.appliances)


@pytest.hookimpl
def pytest_collect_logs(config, appliances):
    if not config.getoption('--collect-logs'):
        return

    for app in appliances:
        try:
            collect_logs(app)
        except Exception as exc:
            logger.exception(f"Failed to collect logs: {exc}")


def collect_logs(app):
    log_files = DEFAULT_FILES
    local_dir = DEFAULT_LOCAL
    try:
        log_files = env.log_collector.log_files
    except (AttributeError, KeyError):
        logger.info('No log_collector.log_files in env, using the default: %s', log_files)
        pass
    try:
        local_dir = log_path.join(env.log_collector.local_dir)
    except (AttributeError, KeyError):
        logger.info('No log_collector.local_dir in env, using the default: %s', local_dir)
        pass

    # Handle local dir existing
    local_dir.ensure(dir=True)

    with app.ssh_client as ssh_client:
        logger.info(f'Starting log collection on appliance {app.hostname}')
        tarred_dir_name = f'log-collector-{app.hostname}'
        # wrap the files in ls, redirecting stderr, to ignore files that don't exist
        tar_dir_path = os.path.join(local_dir.strpath, tarred_dir_name)
        tarball_path = f'{tar_dir_path}.tar.gz'
        os.mkdir(tar_dir_path)
        for f in log_files:
            try:
                ssh_client.get_file(f, tar_dir_path)
            except scp.SCPException as ex:
                logger.error("Failed to transfer file %s: %s", f, ex)
        logger.debug('Creating tar file for appliance %s', app)
        subprocess.run(['tar', '-C', local_dir, '-czvf', tarball_path, tarred_dir_name],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        shutil.rmtree(tar_dir_path)
        logger.info('Wrote the following file %s', tarball_path)


class CollectLogsHookSpecs:
    @pytest.hookspec
    def pytest_collect_logs(config, appliances):
        logger.warning('Executing the hookspec')
        pass
