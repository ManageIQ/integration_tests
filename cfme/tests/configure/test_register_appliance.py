import pytest
import re

from cfme.configure import red_hat_updates
from cfme.web_ui import InfoBlock
from utils import conf, version
from utils.testgen import parametrize
from utils.wait import wait_for
from utils.log import logger


REG_METHODS = ('rhsm', 'sat6')

"""
Tests RHSM and Sat6 registration and checks result over ssh
(update is not performed - it is non-destructive).

For setup, see test_update_appliances.py (red_hat_updates section in cfme_data yaml).

These tests do not check registration results in the web UI, only through SSH.
"""


def pytest_generate_tests(metafunc):
    argnames = ['reg_method', 'reg_data', 'proxy_url', 'proxy_creds']
    argvalues = []
    idlist = []

    stream = version.current_stream()
    try:
        all_reg_data = conf.cfme_data.get('redhat_updates', {})['streams'][stream]
    except KeyError:
        logger.warning('Could not find rhsm data for stream in yaml')
        pytest.mark.uncollect(
            metafunc.function, message='Could not find rhsm data for stream in yaml')
        return

    if 'reg_method' in metafunc.fixturenames:
        for reg_method in REG_METHODS:

            reg_data = all_reg_data.get(reg_method)
            if not reg_data or not reg_data.get('test_registration', False):
                continue

            proxy_data = conf.cfme_data.get('redhat_updates', {}).get('http_proxy', False)
            if proxy_data and reg_data.get('use_http_proxy', False):
                proxy_url = proxy_data['url']
                # proxy_creds_key = proxy_data['credentials']
                # proxy_creds = conf.credentials[proxy_creds_key]
                argval = [reg_method, reg_data, proxy_url, None]
                argid = '{}-{}'.format(reg_method, 'proxy_on')
                idlist.append(argid)
                argvalues.append(argval)

            argval = [reg_method, reg_data, None, None]
            argid = '{}-{}'.format(reg_method, 'proxy_off')
            idlist.append(argid)
            argvalues.append(argval)
        parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


def rhsm_unregister(appliance):
    appliance.ssh_client.run_command('subscription-manager remove --all')
    appliance.ssh_client.run_command('subscription-manager unregister')
    appliance.ssh_client.run_command('subscription-manager clean')


def sat6_unregister(appliance):

        appliance.ssh_client.run_command('subscription-manager remove --all')
        appliance.ssh_client.run_command('subscription-manager unregister')
        appliance.ssh_client.run_command('subscription-manager clean')
        appliance.ssh_client.run_command('mv -f /etc/rhsm/rhsm.conf.kat-backup /etc/rhsm/rhsm.conf')
        appliance.ssh_client.run_command('rpm -qa | grep katello-ca-consumer | xargs rpm -e')


def is_registration_complete(used_repo_or_channel, appliance):
    ret, out = appliance.ssh_client.run_command('yum repolist enabled')
    # Check that the specified (or default) repo (can be multiple, separated by a space)
    # is enabled and that there are packages available
    for repo_or_channel in used_repo_or_channel.split(' '):
        if (repo_or_channel not in out) or (not re.search(r'repolist: [^0]', out)):
            return False
    return True


@pytest.mark.ignore_stream("upstream")
def test_rh_creds_validation(request, reg_method, reg_data, proxy_url, proxy_creds):
    repo = reg_data.get('enable_repo', None)
    if not repo:
        set_default_repo = True
    else:
        set_default_repo = False

    if proxy_url:
        use_proxy = True
        proxy_username = None  # proxy_creds['username']
        proxy_password = None  # proxy_creds['password']
    else:
        use_proxy = False
        proxy_url = None
        proxy_username = None
        proxy_password = None

    red_hat_updates.update_registration(
        service=reg_method,
        url=reg_data['url'],
        username=conf.credentials[reg_method]['username'],
        password=conf.credentials[reg_method]['password'],
        repo_name=repo,
        organization=reg_data.get('organization'),
        use_proxy=use_proxy,
        proxy_url=proxy_url,
        proxy_username=proxy_username,
        proxy_password=proxy_password,
        set_default_repository=set_default_repo,
        cancel=True
    )


@pytest.mark.ignore_stream("upstream")
def test_rh_registration(request, reg_method, reg_data, proxy_url, proxy_creds):

    repo = reg_data.get('enable_repo', None)
    if not repo:
        set_default_repo = True
    else:
        set_default_repo = False

    if proxy_url:
        use_proxy = True
        proxy_username = None  # proxy_creds['username']
        proxy_password = None  # proxy_creds['password']
    else:
        use_proxy = False
        proxy_url = None
        proxy_username = None
        proxy_password = None

    red_hat_updates.update_registration(
        service=reg_method,
        url=reg_data['url'],
        username=conf.credentials[reg_method]['username'],
        password=conf.credentials[reg_method]['password'],
        repo_name=repo,
        organization=reg_data.get('organization'),
        use_proxy=use_proxy,
        proxy_url=proxy_url,
        proxy_username=proxy_username,
        proxy_password=proxy_password,
        set_default_repository=set_default_repo,
        # Satellite 6 registration requires validation to be able to choose organization
        validate=False if reg_method != 'sat6' else True
    )

    used_repo_or_channel = InfoBlock(
        'Red Hat Software Updates', 'Repository Name(s)').text

    red_hat_updates.register_appliances()  # Register all

    if reg_method == 'rhsm':
        request.addfinalizer(rhsm_unregister)
    else:
        request.addfinalizer(sat6_unregister)

    wait_for(
        func=is_registration_complete,
        func_args=[used_repo_or_channel],
        delay=40,
        num_sec=400,
        fail_func=red_hat_updates.register_appliances
    )
