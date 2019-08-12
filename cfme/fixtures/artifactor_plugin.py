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
import os
import subprocess
from threading import RLock

import diaper
import pytest

from artifactor import ArtifactorClient
from cfme.fixtures.pytest_store import store
from cfme.fixtures.pytest_store import write_line
from cfme.markers.polarion import extract_polarion_ids
from cfme.utils.appliance import find_appliance
from cfme.utils.blockers import Blocker
from cfme.utils.blockers import BZ
from cfme.utils.conf import credentials
from cfme.utils.conf import env
from cfme.utils.log import logger
from cfme.utils.net import net_check
from cfme.utils.net import random_port
from cfme.utils.wait import wait_for

UNDER_TEST = False  # set to true for artifactor using tests


# Create a list of all our passwords for use with the sanitize request later in this module
# Filter out all Nones as it will mess the output up.
words = [word for word
         in {v.get('password') for v in credentials.values()}
         if word is not None]


def get_test_idents(item):
    try:
        return item.location[2], item.location[0]
    except AttributeError:
        try:
            return item.fspath.strpath, None
        except AttributeError:
            return (None, None)


def get_name(obj):
    return (getattr(obj, '_param_name', None) or
            getattr(obj, 'name', None) or
            str(obj))


class DummyClient(object):
    def fire_hook(self, *args, **kwargs):
        return

    def terminate(self):
        return

    def task_status(self):
        return

    def __bool__(self):
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
session_fw_version = None


def pytest_addoption(parser):
    parser.addoption("--run-id", action="store", default=None,
                     help="A run id to assist in logging")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if config.getoption('--help'):
        return
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
    from cfme.utils.log import artifactor_handler
    artifactor_handler.artifactor = art_client
    if store.slave_manager:
        artifactor_handler.slaveid = store.slaveid
    config._art_client = art_client


@pytest.fixture(scope='session')
def merkyl_setup(request, appliance):
    fire_art_hook(request.config, 'setup_merkyl', ip=appliance.hostname)


def fire_art_hook(config, hook, **hook_args):
    client = getattr(config, '_art_client', None)
    if client is None:
        assert UNDER_TEST, 'missing artifactor is only valid for inprocess tests'
    else:
        return client.fire_hook(hook, **hook_args)


def fire_art_test_hook(node, hook, **hook_args):
    name, location = get_test_idents(node)
    return fire_art_hook(
        node.config, hook,
        test_name=name,
        test_location=location,
        **hook_args)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item):
    global session_ver
    global session_build
    global session_stream
    appliance = find_appliance(item)
    if not session_ver:
        session_ver = str(appliance.version)
        session_build = appliance.build
        session_stream = appliance.version.stream()
        if str(session_ver) not in session_build:
            session_build = "{}-{}".format(str(session_ver), session_build)
        session_fw_version = None
        try:
            proc = subprocess.Popen(['git', 'describe', '--tags'],
                                    stdout=subprocess.PIPE)
            proc.wait()
            session_fw_version = proc.stdout.read().strip()
        except Exception:
            pass  # already set session_fw_version to None
        fire_art_hook(
            item.config, 'session_info',
            version=session_ver,
            build=session_build,
            stream=session_stream,
            fw_version=session_fw_version
        )

    tier = item.get_closest_marker('tier')
    if tier:
        tier = tier.args[0]

    requirement = item.get_closest_marker('requirement')
    if requirement:
        requirement = requirement.args[0]

    param_dict = {}
    try:
        params = item.callspec.params
        param_dict = {p: get_name(v) for p, v in params.items()}
    except Exception:
        pass  # already set param_dict
    ip = appliance.hostname
    # This pre_start_test hook is needed so that filedump is able to make get the test
    # object set up before the logger starts logging. As the logger fires a nested hook
    # to the filedumper, and we can't specify order inriggerlib.
    meta = item.get_closest_marker('meta')
    if meta and 'blockers' in meta.kwargs:
        blocker_spec = meta.kwargs['blockers']
        blockers = []
        for blocker in blocker_spec:
            if isinstance(blocker, int):
                blockers.append(BZ(blocker).url)
            else:
                blockers.append(Blocker.parse(blocker).url)
    else:
        blockers = []
    fire_art_test_hook(
        item, 'pre_start_test',
        slaveid=store.slaveid, ip=ip)
    fire_art_test_hook(
        item, 'start_test',
        slaveid=store.slaveid, ip=ip,
        tier=tier, requirement=requirement, param_dict=param_dict, issues=blockers)
    yield


def pytest_runtest_teardown(item, nextitem):
    name, location = get_test_idents(item)
    app = find_appliance(item)
    ip = app.hostname
    fire_art_test_hook(
        item, 'finish_test',
        slaveid=store.slaveid, ip=ip, wait_for_task=True)
    fire_art_test_hook(item, 'sanitize', words=words)
    jenkins_data = {
        'build_url': os.environ.get('BUILD_URL'),
        'build_number': os.environ.get('BUILD_NUMBER'),
        'git_commit': os.environ.get('GIT_COMMIT'),
        'job_name': os.environ.get('JOB_NAME')
    }
    param_dict = None
    try:
        caps = app.browser.widgetastic.selenium.capabilities
        param_dict = {
            'browserName': caps['browserName'],
            'browserPlatform': caps['platform'],
            'browserVersion': caps['version']
        }
    except Exception:
        logger.exception("Couldn't grab browser env_vars")
        pass  # already set param_dict

    fire_art_test_hook(
        item, 'ostriz_send', env_params=param_dict,
        slaveid=store.slaveid, polarion_ids=extract_polarion_ids(item), jenkins=jenkins_data)


def pytest_runtest_logreport(report):
    if store.slave_manager:
        return  # each node does its own reporting
    config = store.config  # tech debt
    name, location = get_test_idents(report)
    xfail = hasattr(report, 'wasxfail')

    if hasattr(report, 'skipped'):
        if report.skipped:
            fire_art_hook(
                config, 'filedump',
                test_location=location, test_name=name,
                description="Short traceback",
                contents=report.longreprtext,
                file_type="short_tb", group_id="skipped")
    fire_art_hook(
        config, 'report_test',
        test_location=location, test_name=name,
        test_xfail=xfail, test_when=report.when,
        test_outcome=report.outcome,
        test_phase_duration=report.duration)
    fire_art_hook(config, 'build_report')


@pytest.hookimpl(hookwrapper=True)
def pytest_unconfigure(config):
    yield
    shutdown(config)


lock = RLock()


def shutdown(config):
    app = find_appliance(config, require=False)
    if app is not None:
        with lock:
            proc = config._art_proc
            if proc and proc.returncode is None:
                if not store.slave_manager:
                    write_line('collecting artifacts')
                    fire_art_hook(config, 'finish_session')
                fire_art_hook(config, 'teardown_merkyl',
                              ip=app.hostname)
                if not store.slave_manager:
                    config._art_client.terminate()
                    proc.wait()
