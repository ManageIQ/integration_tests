# -*- coding: utf-8 -*-

import pytest
import re

from cfme.configure import red_hat_updates
from cfme.web_ui import InfoBlock, flash
from utils import conf, error, version
from utils.blockers import BZ
from utils.ssh import SSHClient
from utils.testgen import parametrize
from utils.wait import wait_for


REG_METHODS = ('rhsm', 'sat5', 'sat6')

"""
Tests RHSM, Sat5 and Sat6 registration and checks result over ssh
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
        pytest.mark.uncollect(metafunc.function)
        return

    if 'reg_method' in metafunc.fixturenames:
        for reg_method in REG_METHODS:
            # We cannot validate against Satellite 5
            if metafunc.function.__name__ == 'test_rh_creds_validation' and reg_method == 'sat5':
                continue

            reg_data = all_reg_data.get(reg_method, None)
            if not reg_data or not reg_data.get('test_registration', False):
                continue

            proxy_data = conf.cfme_data['redhat_updates'].get('http_proxy', False)
            if proxy_data and reg_data.get('use_http_proxy', False):
                proxy_url = proxy_data['url']
                proxy_creds_key = proxy_data['credentials']
                proxy_creds = conf.credentials[proxy_creds_key]
                argval = [reg_method, reg_data, proxy_url, proxy_creds]
                argid = '{}-{}'.format(reg_method, 'proxy_on')
                idlist.append(argid)
                argvalues.append(argval)

            argval = [reg_method, reg_data, None, None]
            argid = '{}-{}'.format(reg_method, 'proxy_off')
            idlist.append(argid)
            argvalues.append(argval)
        parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


# We must make sure that org ID is unset (because of BZ#1048997)
@pytest.fixture
def unset_org_id():
    try:
        red_hat_updates.update_registration(
            service='sat5',
            url="http://not.used.for.reg/XMLRPC",
            username='not_used_for_reg',
            password='not_used_for_reg',
            organization=''
        )
    except Exception as ex:
        # Did this happen because the save button was dimmed?
        try:
            # If so, its fine - just return
            if red_hat_updates.form_buttons.save.is_dimmed:
                return
        except:
            # And if we cant access the save button
            pass
        # Something else happened so return the original exception
        raise ex


def rhsm_unregister():
    with SSHClient() as ssh:
        ssh.run_command('subscription-manager remove --all')
        ssh.run_command('subscription-manager unregister')
        ssh.run_command('subscription-manager clean')


def sat5_unregister():
    with SSHClient() as ssh:
        ssh.run_command('rm -f /etc/sysconfig/rhn/systemid')


def sat6_unregister():
    with SSHClient() as ssh:
        ssh.run_command('subscription-manager remove --all')
        ssh.run_command('subscription-manager unregister')
        ssh.run_command('subscription-manager clean')
        ssh.run_command('mv -f /etc/rhsm/rhsm.conf.kat-backup /etc/rhsm/rhsm.conf')
        ssh.run_command('rpm -qa | grep katello-ca-consumer | xargs rpm -e')


def is_registration_complete(used_repo_or_channel):
    with SSHClient() as ssh:
        ret, out = ssh.run_command('yum repolist enabled')
        # Check that the specified (or default) repo (can be multiple, separated by a space)
        # is enabled and that there are packages available
        for repo_or_channel in used_repo_or_channel.split(' '):
            if (repo_or_channel not in out) or (not re.search(r'repolist: [^0]', out)):
                return False
        return True


@pytest.mark.ignore_stream("upstream")
@pytest.mark.meta(
    blockers=[
        BZ(1198111, unblock=lambda reg_method: reg_method not in {'rhsm', 'sat6'})
    ]
)
def test_rh_creds_validation(request, unset_org_id,
                             reg_method, reg_data, proxy_url, proxy_creds):
    if reg_method in ('rhsm', 'sat6'):
        repo_or_channel = reg_data.get('enable_repo', None)
    else:
        repo_or_channel = reg_data.get('add_channel', None)

    if not repo_or_channel:
        set_default_repo = True
    else:
        set_default_repo = False

    if proxy_url:
        use_proxy = True
        proxy_username = proxy_creds['username']
        proxy_password = proxy_creds['password']
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
        repo_name=repo_or_channel,
        organization=reg_data.get('organization', None),
        use_proxy=use_proxy,
        proxy_url=proxy_url,
        proxy_username=proxy_username,
        proxy_password=proxy_password,
        set_default_repository=set_default_repo,
        cancel=True
    )


@pytest.mark.ignore_stream("upstream")
@pytest.mark.meta(
    blockers=[
        BZ(1102724, unblock=lambda proxy_url: proxy_url is None),
        # Sat6 requires validation to register
        BZ(1198111, unblock=lambda reg_method: reg_method != 'sat6')
    ]
)
def test_rh_registration(request, unset_org_id,
                         reg_method, reg_data, proxy_url, proxy_creds):

    if reg_method in ('rhsm', 'sat6'):
        repo_or_channel = reg_data.get('enable_repo', None)
    else:
        repo_or_channel = reg_data.get('add_channel', None)

    if not repo_or_channel:
        set_default_repo = True
    else:
        set_default_repo = False

    if proxy_url:
        use_proxy = True
        proxy_username = proxy_creds['username']
        proxy_password = proxy_creds['password']
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
        repo_name=repo_or_channel,
        organization=reg_data.get('organization', None),
        use_proxy=use_proxy,
        proxy_url=proxy_url,
        proxy_username=proxy_username,
        proxy_password=proxy_password,
        set_default_repository=set_default_repo,
        # Satellite 6 registration requires validation to be able to choose organization
        validate=False if reg_method != 'sat6' else True
    )

    used_repo_or_channel = InfoBlock('Red Hat Software Updates', version.pick({
        version.LOWEST: 'Update Repository',
        "5.4": 'Channel Name(s)' if reg_method == 'sat5' else 'Repository Name(s)'})
    ).text

    red_hat_updates.register_appliances()  # Register all

    if reg_method == 'rhsm':
        request.addfinalizer(rhsm_unregister)
    elif reg_method == 'sat5':
        request.addfinalizer(sat5_unregister)
    else:
        request.addfinalizer(sat6_unregister)

    wait_for(
        func=is_registration_complete,
        func_args=[used_repo_or_channel],
        delay=40,
        num_sec=400,
        fail_func=red_hat_updates.register_appliances
    )


@pytest.mark.ignore_stream("upstream")
def test_sat5_incorrect_url_format_check(request, unset_org_id):
    # Check that we weren't allowed to save the data
    with error.expected('No matching flash message'):
        red_hat_updates.update_registration(
            service="sat5",
            url="url.not.matching.format.example.com",
            username="not_used",
            password="not_used"
        )
    # Confirm that it was the Sat5 url check that blocked it
    flash.assert_message_contain("https://server.example.com/XMLRPC")
