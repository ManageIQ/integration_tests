# -*- coding: utf-8 -*-

import pytest
import re

from cfme.fixtures import pytest_selenium as sel
from cfme.configure import red_hat_updates
from cfme.web_ui import InfoBlock
from utils import conf
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
    all_reg_data = conf.cfme_data['redhat_updates']['registration']
    if 'reg_method' in metafunc.fixturenames:
        for reg_method in REG_METHODS:
            reg_data = all_reg_data.get(reg_method, None)
            if not reg_data or not reg_data.get('test_registration', False):
                continue

            proxy_data = all_reg_data.get('http_proxy', False)
            if proxy_data and proxy_data.get('url', None):
                proxy_url = proxy_data['url']
                proxy_creds = conf.credentials['http_proxy']
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
            url=None,
            username=None,
            password=None,
            organization=''
        )
    except sel.NoSuchElementException:
        pass


def rhsm_sat6_unregister():
    with SSHClient() as ssh:
        ssh.run_command('subscription-manager remove --all')
        ssh.run_command('subscription-manager unregister')


def sat5_unregister():
    with SSHClient() as ssh:
        ssh.run_command('rm -f /etc/sysconfig/rhn/systemid')


def is_registration_complete(used_repo_or_channel):
    with SSHClient() as ssh:
        ret, out = ssh.run_command('yum repolist enabled')
        # Check that the specified (or default) repo is enabled and that there are
        # packages available
        if used_repo_or_channel in out and re.search(r'repolist: [^0]', out):
            return True
        return False


# Currently fails on 5.3 (0528) when using proxy BZ#1102724
@pytest.mark.downstream
def test_appliance_registration(request, unset_org_id,
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
        set_default_repository=set_default_repo
    )

    used_repo_or_channel = InfoBlock("form").text('Red Hat Software Updates', 'Update Repository')

    red_hat_updates.register_appliances()  # Register all

    if reg_method in ('rhsm', 'sat6'):
        request.addfinalizer(rhsm_sat6_unregister)
    elif reg_method == 'sat5':
        request.addfinalizer(sat5_unregister)

    wait_for(
        func=is_registration_complete,
        func_args=[used_repo_or_channel],
        delay=15,
        num_sec=180
    )
