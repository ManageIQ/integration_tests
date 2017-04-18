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
import atexit
from urlparse import urlparse

import diaper
import pytest

from artifactor import ArtifactorClient
from fixtures.pytest_store import write_line, store
from markers.polarion import extract_polarion_ids
from threading import RLock
from utils.conf import env, credentials
from utils.net import random_port, net_check
from utils.wait import wait_for
from utils import version

UNDER_TEST = False  # set to true for artifactor using tests


# Create a list of all our passwords for use with the sanitize request later in this module
words = []
for cred in credentials:
    word = credentials[cred].get('password', None)
    if word:
        words.append(word)


def get_test_idents(item):
    try:
        return item.location[2], item.location[0]
    except AttributeError:
        try:
            return item.fspath.strpath, None
        except AttributeError:
            return (None, None)


def get_name(obj):
    return getattr(obj, '_param_name', None) or getattr(obj, 'name', None) or str(obj)


class DummyClient(object):
    def fire_hook(self, *args, **kwargs):
        return

    def terminate(self):
        return

    def task_status(self):
        return

    def __nonzero__(self):
        # DummyClient is always False,
        # so it's easy to see if we have an artiactor client
        return False


def get_client(art_config, pytest_config):
    if art_config and not UNDER_TEST:
        port = getattr(pytest_config.option, 'artifactor_port', None) or \
            art_config.get('server_port') or random_port()
        pytest_config.option.artifactor_port = port
        art_config['server_port'] = port
        return ArtifactorClient(
            art_config['server_address'], art_config['server_port'])
    else:
        return DummyClient()


def spawn_server(config, art_client):
    if store.slave_manager or UNDER_TEST:
        return None
    import subprocess
    cmd = ['miq-artifactor-server', '--port', str(art_client.port)]
    if config.getvalue('run_id'):
        cmd.append('--run-id')
        cmd.append(str(config.getvalue('run_id')))
    proc = subprocess.Popen(cmd)
    return proc


session_ver = None
session_build = None
session_stream = None


def pytest_addoption(parser):
    parser.addoption("--run-id", action="store", default=None,
                     help="A run id to assist in logging")


@pytest.mark.tryfirst
def pytest_configure(config):
    art_client = get_client(
        art_config=env.get('artifactor', {}),
        pytest_config=config)

    # just in case
    if not store.slave_manager:
        with diaper:
            atexit.register(shutdown, config)

    if art_client:
        config._art_proc = spawn_server(config, art_client)
        wait_for(
            net_check,
            func_args=[art_client.port, '127.0.0.1'],
            func_kwargs={'force': True},
            num_sec=10, message="wait for artifactor to start")
        art_client.ready = True
    else:
        config._art_proc = None
    from utils.log import artifactor_handler
    artifactor_handler.artifactor = art_client
    config._art_client = art_client
    art_client.fire_hook('setup_merkyl', ip=urlparse(env['base_url']).netloc)


def fire_art_hook(config, hook, **hook_args):
    client = getattr(config, '_art_client', None)
    if client is None:
        assert UNDER_TEST, 'missing artifactor is only valid for inprocess tests'
    else:
        client.fire_hook(hook, **hook_args)


def fire_art_test_hook(node, hook, **hook_args):
    name, location = get_test_idents(node)
    fire_art_hook(
        node.config, hook,
        test_name=name,
        test_location=location,
        **hook_args)


@pytest.mark.hookwrapper
def pytest_runtest_protocol(item):
    global session_ver
    global session_build
    global session_stream

    if not session_ver:
        session_ver = str(version.current_version())
        session_build = store.current_appliance.build
        session_stream = store.current_appliance.version.stream()
        fire_art_hook(
            item.config, 'session_info',
            version=session_ver,
            build=session_build,
            stream=session_stream)

    tier = item.get_marker('tier')
    if tier:
        tier = tier.args[0]

    try:
        params = item.callspec.params
        param_dict = {p: get_name(v) for p, v in params.iteritems()}
    except:
        param_dict = {}
    ip = urlparse(env['base_url']).netloc
    # This pre_start_test hook is needed so that filedump is able to make get the test
    # object set up before the logger starts logging. As the logger fires a nested hook
    # to the filedumper, and we can't specify order inriggerlib.
    fire_art_test_hook(
        item, 'pre_start_test',
        slaveid=store.slaveid, ip=ip)
    fire_art_test_hook(
        item, 'start_test',
        slaveid=store.slaveid, ip=ip,
        tier=tier, param_dict=param_dict)
    yield


def pytest_runtest_teardown(item, nextitem):
    name, location = get_test_idents(item)
    ip = urlparse(env['base_url']).netloc
    fire_art_test_hook(
        item, 'finish_test',
        slaveid=store.slaveid, ip=ip, grab_result=True)
    fire_art_test_hook(item, 'sanitize', words=words)
    fire_art_test_hook(
        item, 'ostriz_send',
        slaveid=store.slaveid, polarion_ids=extract_polarion_ids(item))


def pytest_runtest_logreport(report):
    config = pytest.config  # tech debt
    name, location = get_test_idents(report)
    if hasattr(report, 'wasxfail'):
        xfail = True
    else:
        xfail = False

    if hasattr(report, 'skipped'):
        if report.skipped:
            try:
                contents = report.longrepr[2]
            except AttributeError:
                contents = str(report.longrepr)
            fire_art_hook(
                config, 'filedump',
                test_location=location, test_name=name,
                description="Short traceback", contents=contents,
                file_type="short_tb", group_id="skipped")
    fire_art_hook(
        config, 'report_test',
        test_location=location, test_name=name,
        test_xfail=xfail, test_when=report.when,
        test_outcome=report.outcome)
    fire_art_hook(config, 'build_report')


@pytest.mark.hookwrapper
def pytest_unconfigure(config):
    yield
    shutdown(config)


lock = RLock()


def shutdown(config):
    with lock:
        proc = config._art_proc
        if proc:
            if not store.slave_manager:
                write_line('collecting artifacts')
                fire_art_hook(config, 'finish_session')
            fire_art_hook(config, 'teardown_merkyl',
                          ip=urlparse(env['base_url']).netloc)
            if not store.slave_manager:
                config._art_client.terminate()
                proc = config._art_proc
                if proc:
                    proc.wait()
