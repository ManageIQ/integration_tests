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
from artifactor.plugins import merkyl, logger, video, filedump, reporter
from artifactor import parse_setup_dir
import pytest
from urlparse import urlparse
from utils.conf import env
from utils.path import log_path


art = artifactor.artifactor
art_config = env.get('artifactor', {})
if art_config:
    if 'log_dir' not in art_config:
        art_config['log_dir'] = log_path.join('artifacts').strpath
    art.set_config(art_config)

    art.register_plugin(merkyl.Merkyl, "merkyl")
    art.register_plugin(logger.Logger, "logger")
    art.register_plugin(video.Video, "video")
    art.register_plugin(filedump.Filedump, "filedump")
    art.register_plugin(reporter.Reporter, "reporter")
    art.register_hook_callback('filedump', 'pre', parse_setup_dir, name="filedump_dir_setup")

    artifactor.initialize()
ip = urlparse(env['base_url']).hostname


def pytest_addoption(parser):
    parser.addoption("--run-id", action="store", default=None,
                     help="A run id to assist in logging")


@pytest.mark.tryfirst
def pytest_configure(config):
    if art.initialized:
        art.configure_plugin('merkyl', ip=ip)
        art.configure_plugin('logger')
        art.configure_plugin('video')
        art.configure_plugin('filedump')
        art.configure_plugin('reporter')
    art.fire_hook('start_session', run_id=config.getvalue('run_id'))


def pytest_runtest_protocol(item):
    art.fire_hook('start_test', test_location=item.location[0], test_name=item.location[2])


def pytest_runtest_teardown(item, nextitem):
    art.fire_hook('finish_test', test_location=item.location[0], test_name=item.location[2])


def pytest_runtest_logreport(report):
    art.fire_hook('report_test', test_location=report.location[0], test_name=report.location[2],
                  test_report=report)
    art.fire_hook('build_report')


@pytest.mark.trylast
def pytest_unconfigure():
    art.fire_hook('finish_session')
