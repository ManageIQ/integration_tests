"""An example config::

    artifactor:
        log_dir: /home/test/workspace/cfme_tests/artiout
        per_run: test #test, run, None
        reuse_dir: True
        squash_exceptions: False
        threaded: False
        server_address: 127.0.0.1
        server_port: 21212
        server_enabled: True
        plugins:

``log_dir`` is the destination for all artifacts

``per_run`` denotes if the test artifacts should be group by run, test, or None

``reuse_dir`` if this is False and Artifactor comes across a dir that has
already been used, it will die
"""

from urlparse import urlparse

from artifactor import ArtifactorClient
import pytest
from utils.conf import env, credentials
from utils.net import random_port, net_check
from utils.path import project_path
from utils.wait import wait_for
import atexit


class DummyClient(object):
    def fire_hook(self, *args, **kwargs):
        return

    def __nonzero__(self):
        # DummyClient is always False, so it's easy to see if we have an artiactor client
        return False

proc = None

art_config = env.get('artifactor', {})

if art_config:
    # If server_port isn't set, pick a random port
    if 'server_port' not in art_config:
        port = random_port()
        art_config['server_port'] = port
    art_client = ArtifactorClient(art_config['server_address'], art_config['server_port'])
else:
    art_client = DummyClient()

SLAVEID = ""
if env.get('slaveid', None):
    SLAVEID = env['slaveid']


appliance_ip_address = urlparse(env['base_url']).netloc


def pytest_addoption(parser):
    parser.addoption("--run-id", action="store", default=None,
                     help="A run id to assist in logging")


@pytest.mark.tryfirst
def pytest_configure(config):
    global proc
    if not SLAVEID and not proc and isinstance(art_client, ArtifactorClient):
        import subprocess
        path = project_path.join('utils', 'artifactor_start.py')
        cmd = [path.strpath]
        cmd.append('--port')
        cmd.append(str(art_client.port))
        if config.getvalue('run_id'):
            cmd.append('--run-id')
            cmd.append(str(config.getvalue('run_id')))
        proc = subprocess.Popen(cmd)
        wait_for(net_check, func_args=[art_client.port, '127.0.0.1'], func_kwargs={'force': True},
                 num_sec=10, message="wait for artifactor to start")
        config.option.artifactor_port = art_client.port
    elif isinstance(art_client, ArtifactorClient):
        art_client.port = config.option.artifactor_port
    art_client.fire_hook('setup_merkyl', ip=appliance_ip_address)


def pytest_runtest_protocol(item):
    art_client.fire_hook('start_test', test_location=item.location[0], test_name=item.location[2],
                         slaveid=SLAVEID, ip=appliance_ip_address)


def pytest_runtest_teardown(item, nextitem):
    words = []
    for cred in credentials:
        word = credentials[cred].get('password', None)
        if word:
            words.append(word)
    art_client.fire_hook('finish_test', test_location=item.location[0], test_name=item.location[2],
                         slaveid=SLAVEID, ip=appliance_ip_address)
    art_client.fire_hook('sanitize', test_location=item.location[0], test_name=item.location[2],
                         fd_idents=['func_trace'], words=words)


def pytest_runtest_logreport(report):
    if hasattr(report, 'wasxfail'):
        xfail = True
    else:
        xfail = False
    art_client.fire_hook('report_test', test_location=report.location[0],
                         test_name=report.location[2], test_xfail=xfail, test_when=report.when,
                         test_outcome=report.outcome)
    art_client.fire_hook('build_report')


@pytest.mark.trylast
def pytest_unconfigure():
    global proc
    if not SLAVEID:
        art_client.fire_hook('finish_session')
    art_client.fire_hook('teardown_merkyl', ip=appliance_ip_address)
    if not SLAVEID:
        art_client.fire_hook('terminate')


if not SLAVEID:
    atexit.register(art_client.fire_hook, 'finish_session')
    atexit.register(art_client.fire_hook, 'terminate')
