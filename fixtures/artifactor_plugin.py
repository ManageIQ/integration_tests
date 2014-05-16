"""
artifactor:
    log_dir: /home/test/workspace/cfme_tests/artiout
    per_run: test #test, run, None
    overwrite: True
    plugins:

``log_dir`` is the destination for all artifacts

``per_run`` denotes if the test artifacts should be group by run, test, or None

``overwrite`` if this is False and Artifactor comes across a dir that has
already been used, it will die
"""
import artifactor
from artifactor.plugins import merkyl, logger
import pytest
from urlparse import urlparse
from utils.conf import env


art = artifactor.artifactor
art.set_config(env.get('artifactor', {}))
art.register_plugin(merkyl.Merkyl, "merkyl")
art.register_plugin(logger.Logger, "logger")
artifactor.initialize()
ip = urlparse(env['base_url']).hostname


def pytest_addoption(parser):
    parser.addoption("--run-id", action="store", default=None,
                     help="A run id to assist in logging")


@pytest.mark.tryfirst
def pytest_configure(config):
    files = art.get_instance_data('merkyl').get('log_files', [])
    port = art.get_instance_data('merkyl').get('port', 8192)
    art.get_instance_obj('merkyl').configure(ip=ip, files=files, port=port)
    art.get_instance_obj('logger').configure()
    art.fire_hook('start_session', run_id=config.getvalue('run_id'))


def pytest_runtest_protocol(item):
    art.fire_hook('start_test', test_name=item.name, test_location=item.parent.name)


@pytest.mark.trylast
def pytest_runtest_teardown(item, nextitem):
    art.fire_hook('finish_test', test_location=item.parent.name, test_name=item.name)


@pytest.mark.trylast
def pytest_unconfigure():
    art.fire_hook('finish_session')
