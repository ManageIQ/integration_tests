# -*- coding: utf-8 -*-

"""
@author: apagac@redhat.com
@author: jkrocil@redhat.com
"""

from cfme.configure.configuration import set_server_roles
from cfme.configure import red_hat_updates
from utils import conf
from utils.appliance import provision_appliance_set
from utils.log import logger
from utils.wait import wait_for, TimedOutError
import pytest

# Refresh interval used in wait_for
REFRESH_SEC = 15

"""
Used cfme_data.yaml section explained:
--------------------------------------

redhat_updates:
    current_version: 1.3.3  # Version to check against after update
    registration:
        rhsm:
            url: subscription.rhn.redhat.com  # Server address (web UI field)
            use_http_proxy: False             # Set to True to use proxy server
            enable_repo: cfme-repo-name       # Repository to subscribe to (web UI field)
            test_direct: True                 # Set to True to test regular, direct update
            test_rhn_mirror: True             # Set to True to test content proxy (RHN mirror role)
        sat5:
            url: https://sat5.example.com/XMLRPC  # Server address (web UI field)
            use_http_proxy: False                 # Set to True to use proxy server
            add_channel: cfme-channel-name        # Channel to add (web UI field)
            organization: 2                       # Organization ID to use (web UI field)
            test_direct: False                    # Set to True to test regular, direct update
        sat6:
            url: https://sat6.example.com  # Server address (web UI field)
            use_http_proxy: False          # Set to True to use proxy server
            enable_repo: cfme-repo-name    # Repository to subscribe to (web UI field)
            test_direct: False             # Set to True to test regular, direct update
            test_rhn_mirror: False         # Set to True to test content proxy (RHN mirror role)
        http_proxy:
            url: 10.0.0.1:1234  # Address[:port] of proxy server
    appliances:
        EVM:                # must match an appliance name from appliance_provisioning yaml section
            register: True  # Set to True to register the appliance
            update: True    # Set to True to update the appliance
        EVM_2:
            register: True
            update: True
        EVM_3:
            register: True
            update: False
    download_repo_files:  # Repository files to download after registration but before updating
        - url: http://example.com/path/to/CFME.repo  # URL of the repository to download
          reg_methods:  # List of registration methods this specific repo applies to
              - rhsm    # Can be one of: rhsm, sat5, sat6, rhn_mirror*
    enable_repos:  # Repositories to enable after downloading of repository files
        - name: rhel-6-server-cfme-repo  # Name of the repository to enable
          reg_methods:
              - rhsm
              - sat5
    add_channels:  # Channels to add after registration but before updating (sat5 only)
        - rhel-6-server-cfme-channel

* rhn_mirror is not really a registration method, but we might need to target it when
  downloading or enabling repositories...  ¯\_(ツ)_/¯
"""


@pytest.fixture(scope='module')
def rh_updates_data(cfme_data):
    return cfme_data.get('redhat_updates', {})


@pytest.fixture(scope='module')
def appliances_to_register(rh_updates_data):
    """Names of all appliances with 'register' key set to True
    """
    appliance_names = []
    for appliance_name, appliance_data in rh_updates_data['appliances'].iteritems():
        if appliance_data.get('register', False):
            appliance_names.append(appliance_name)
    return appliance_names


@pytest.fixture(scope='module')
def appliances_to_update(rh_updates_data):
    """Names of all appliances with 'update' key set to True
    """
    appliance_names = []
    for appliance_name, appliance_data in rh_updates_data['appliances'].iteritems():
        if appliance_data.get('update', False):
            appliance_names.append(appliance_name)
    return appliance_names


@pytest.yield_fixture(scope='function')
def appliance_set(cfme_data):
    appliance_set_data = cfme_data.get('appliance_provisioning', {})['appliance_set']
    appliance_set = provision_appliance_set(appliance_set_data, 'rh_updates')

    yield appliance_set

    # Unregister and destroy all
    for appliance in appliance_set.all_appliances:
        with appliance.ssh_client as ssh:
            ssh.run_command('subscription-manager remove --all')
            ssh.run_command('subscription-manager unregister')
        appliance.destroy()


def update_registration(appliance_set, rh_updates_data, reg_method):
    reg_data = rh_updates_data['registration'][reg_method]
    test_proxy = reg_data.get('use_http_proxy', False)

    if test_proxy:
        proxy = rh_updates_data['registration']['http_proxy']
        proxy_creds = conf.credentials['http_proxy']
    else:
        proxy = None
        proxy_creds = {}

    if reg_method in ('rhsm', 'sat6'):
        repo_or_channel = reg_data.get('enable_repo', None)
    else:
        repo_or_channel = reg_data.get('add_channel', None)

    with appliance_set.primary.browser_session():
        red_hat_updates.update_registration(
            service=reg_method,
            url=reg_data['url'],
            username=conf.credentials[reg_method]['username'],
            password=conf.credentials[reg_method]['password'],
            repo_name=repo_or_channel,
            organization=reg_data.get('organization', None),
            use_proxy=test_proxy,
            proxy_url=proxy['url'],
            proxy_username=proxy_creds['username'],
            proxy_password=proxy_creds['password']
        )


def register_appliances(appliance_set, appliances_to_register):
    with appliance_set.primary.browser_session():
        red_hat_updates.register_appliances(*appliances_to_register)

        logger.info('Waiting for appliance statuses to change to Registered')
        wait_for(red_hat_updates.are_registered,
                 func_args=appliances_to_register,
                 num_sec=120,
                 delay=REFRESH_SEC,
                 fail_func=red_hat_updates.refresh)
        logger.info('Done')

        logger.info('Waiting for implicit update check after registration')
        # The update check doesnt have to find any available updates, but it still has to run
        wait_for(red_hat_updates.checked_updates,
                 func_args=appliances_to_register,
                 num_sec=300,
                 delay=REFRESH_SEC,
                 fail_func=red_hat_updates.refresh)
        logger.info('Done')

        # And all registered appliances should be registered and subscribed
        assert red_hat_updates.are_registered(appliances_to_register),\
            'Failed to register all specified appliances'
        assert red_hat_updates.are_subscribed(appliances_to_register),\
            'Failed to subscribe all specified appliances'


def download_repo_files(appliance_set, rh_updates_data, reg_method, target_appliances):
    """Downloads repository files to appliances

    Note:
        Specified in yaml by registration methods: rhsm|sat5|sat6|rhn_mirror (special case)
    """
    download_repos = rh_updates_data.get('download_repo_files') or []
    download_curr_method = [repo['url'] for repo in download_repos
                            if reg_method in repo.get('reg_methods', [])]

    if not download_curr_method:
        return

    download_repos_str = "wget --no-check-certificate --directory-prefix=/etc/yum.repos.d/ {}"\
                         .format(' '.join(download_curr_method))

    for appliance_name in target_appliances:
        appliance = appliance_set.find_by_name(appliance_name)
        with appliance.ssh_client as ssh:
            status, output = ssh.run_command(download_repos_str)
            assert status == 0, 'Failed to download specified repository files on machine {}'\
                                .format(appliance.address)


def enable_repos(appliance_set, rh_updates_data, reg_method, target_appliances):
    """Enables repositories on appliances using ssh

    Note:
        Specified in yaml by registration methods: rhsm|sat5|sat6|rhn_mirror (special case)
    """
    enable_repos = rh_updates_data.get('enable_repos') or []
    enable_curr_method = [repo['name'] for repo in enable_repos
                          if reg_method in repo.get('reg_methods', [])]

    if not enable_curr_method:
        return

    enable_repos_str = 'yum-config-manager --enable {}'.format(' '.join(enable_curr_method))

    for appliance_name in target_appliances:
        appliance = appliance_set.find_by_name(appliance_name)
        with appliance.ssh_client as ssh:
            for repo_name in enable_repos:
                # Get first column from 'yum' using 'cut' and grep for repo with matching name
                is_repo_disabled_str = "yum repolist disabled | cut -f1 -d' ' | grep '{}'"\
                                       .format(repo_name)
                status, output = ssh.run_command(is_repo_disabled_str)
                assert status == 0, 'Repo {} is not disabled on machine {}'\
                                    .format(repo_name, appliance.address)
            status, output = ssh.run_command(enable_repos_str)
            assert status == 0, 'Failed to enable specified repositories on machine {}'\
                                .format(appliance.address)


def add_channels(appliance_set, rh_updates_data, appliances_to_update):
    """Adds channels on appliances_to_update using ssh
    """
    add_channels = rh_updates_data.get('add_channels') or []
    if not add_channels:
        return

    # We must prepend the -c parameter to each channel and join them all with spaces inbetween
    add_channels = ' '.join(['-c ' + channel for channel in add_channels])

    reg_creds = conf.credentials['sat5']
    add_channels_str = 'rhn-channel -a {} -u {} -p {}'\
                       .format(add_channels, reg_creds['username'], reg_creds['password'])

    for appliance_name in appliances_to_update:
        appliance = appliance_set.find_by_name(appliance_name)
        with appliance.ssh_client as ssh:
            status, output = ssh.run_command(add_channels_str)
            assert status == 0, 'Failed to add specified channels on machine {}'\
                                .format(appliance.address)


def rhn_mirror_setup(appliance_set):
    """Sets up RHN mirror feature on primary appliance and checks secondary are subscribed
    """

    with appliance_set.primary.browser_session():
        set_server_roles(rhn_mirror=True)

    appliance_set.primary.restart_evm_service()

    with appliance_set.primary.ssh_client as ssh:
        def is_repotrack_running():
            status, output = ssh.run_command('pgrep repotrack')
            if status == 0:
                return True
            return False

        logger.info('Waiting for repotrack to start')
        wait_for(func=is_repotrack_running, delay=REFRESH_SEC, num_sec=300)
        logger.info('Done')

        logger.info('Waiting for repotrack to finish')
        wait_for(func=is_repotrack_running, delay=REFRESH_SEC, fail_condition=True, num_sec=900)
        logger.info('Done')

        # Check that repo folder exists on primary and contains cfme-appliance pkg
        assert ssh.run_command('ls -m1 /repo/mirror | grep cfme-appliance')[0] == 0,\
            "/repo/mirror on {} doesn't exist or doesn't contain cfme-appliance pkg"\
            .format(appliance_set.primary.name)

    logger.info('Waiting for web UI to start')
    appliance_set.primary.wait_for_web_ui()
    logger.info('Done')

    # Check /etc/yum.repos.d/cfme-mirror.repo file exists on secondary appliances
    for appliance in appliance_set.secondary:
        with appliance.ssh_client as ssh:
            def repo_file_exists():
                status, output = ssh.run_command('ls /etc/yum.repos.d/cfme-mirror.repo')
                if status == 0:
                    return True
                return False

            logger.info('Waiting for repository files to be created on secondary appliances')
            wait_for(func=repo_file_exists, delay=REFRESH_SEC, num_sec=120)
            logger.info('Done')

    # And confirm that all appliances are subscribed
    with appliance_set.primary.browser_session():
        assert red_hat_updates.are_subscribed(),\
            'Failed to subscribe all appliances (secondary via proxy)'


def run_cfme_updates(appliance_set, rh_updates_data, appliances_to_update):
    """Runs CFME update on appliances_to_update using web UI of primary appliance

    Note:
        Just a heads up - CFME 5.3+ will, on non-db appliances, apply platform updates
        along with cfme updates.
    """
    with appliance_set.primary.browser_session():
        red_hat_updates.update_appliances(*appliances_to_update)

        version_match_args = [rh_updates_data['current_version']] + appliances_to_update

        # If primary will be updated too
        if appliance_set.primary.name in appliances_to_update:
            logger.info('Waiting for web UI to stop')
            appliance_set.primary.wait_for_web_ui(timeout=120, running=False)
            logger.info('Done')

            logger.info('Waiting for web UI to start')
            appliance_set.primary.wait_for_web_ui(timeout=600)
            logger.info('Done')

            # Primary is up to date now but secondaries might still need some time
            version_check_wait_sec = 120

        else:
            # Primary will not be updated but we still need to wait for secondaries the full time
            version_check_wait_sec = 720

    with appliance_set.primary.browser_session():
        logger.info('Waiting for appliances to update (checking versions)')
        wait_for(red_hat_updates.versions_match,
                 func_args=version_match_args,
                 num_sec=version_check_wait_sec,
                 delay=REFRESH_SEC,
                 fail_func=red_hat_updates.refresh)
        logger.info('Done')


def run_platform_updates(appliance_set, appliances_to_update):
    """Runs platform update on appliances_to_update using ssh
    """
    with appliance_set.primary.browser_session():
        primary_will_be_updated = False
        for appliance_name in appliances_to_update:
            appliance = appliance_set.find_by_name(appliance_name)
            with appliance.ssh_client as ssh:
                status, output = ssh.run_command('yum check-update')
                # 100 == there are packages available for update on this appliance
                if status != 100:
                    continue
                if appliance_name == appliance_set.primary.name:
                    primary_will_be_updated = True
                status, output = ssh.run_command('yum update -y &')
                assert status == 0, 'Failed to start platform updates on machine {}'\
                                    .format(appliance.address, output)

        # If primary will be updated too
        if primary_will_be_updated:
            try:
                # If the web UI doesn't go down in 120sec
                logger.info('Waiting to check if web UI will stop')
                appliance_set.primary.wait_for_web_ui(timeout=120, running=False)
            except TimedOutError:
                # we can proceed, because it won't go down at all
                logger.info("Done - web UI didn't stop")
            else:
                # else, we will have to wait for it to come up again
                logger.info("Done - web UI stopped")
                logger.info("Waiting for web UI to start")
                appliance_set.primary.wait_for_web_ui(timeout=600)
                logger.info("Done")

        def check_updates_and_refresh():
            red_hat_updates.check_updates(*appliances_to_update)
            red_hat_updates.refresh()

    with appliance_set.primary.browser_session():
        logger.info("Waiting for platform update statuses to change")
        wait_for(red_hat_updates.platform_updates_available,
                 func_args=appliances_to_update,
                 num_sec=900,
                 delay=REFRESH_SEC,
                 fail_condition=True,
                 fail_func=check_updates_and_refresh)
        logger.info("Done")

try:
    skip_rhsm_direct = not conf.cfme_data.redhat_updates.registration.rhsm.test_direct
except KeyError:
    skip_rhsm_direct = True


@pytest.mark.uncollectif(skip_rhsm_direct,
    reason='RH Update test using RHSM is not enabled')
@pytest.mark.long_running
def test_rhsm_direct(appliance_set, rh_updates_data,
                     appliances_to_register, appliances_to_update):
    update_registration(appliance_set, rh_updates_data, 'rhsm')
    register_appliances(appliance_set, appliances_to_register)

    download_repo_files(appliance_set, rh_updates_data, 'rhsm', appliances_to_update)
    enable_repos(appliance_set, rh_updates_data, 'rhsm', appliances_to_update)

    run_cfme_updates(appliance_set, rh_updates_data, appliances_to_update)
    run_platform_updates(appliance_set, appliances_to_update)

try:
    skip_rhsm_rhn_mirror = not conf.cfme_data.redhat_updates.registration.rhsm.test_rhn_mirror
except KeyError:
    skip_rhsm_rhn_mirror = True


@pytest.mark.uncollectif(skip_rhsm_rhn_mirror,
    reason='RH Update test using RHSM/RHN Mirror is not enabled')
@pytest.mark.long_running
def test_rhsm_rhn_mirror(appliance_set, rh_updates_data, appliances_to_update):
    # Use only primary to register_appliances(), download_repo_files() and enable_repos()
    target_appliances = [appliance_set.primary.name]

    update_registration(appliance_set, rh_updates_data, 'rhsm')
    register_appliances(appliance_set, target_appliances)

    download_repo_files(appliance_set, rh_updates_data, 'rhn_mirror', target_appliances)
    enable_repos(appliance_set, rh_updates_data, 'rhn_mirror', target_appliances)
    rhn_mirror_setup(appliance_set)

    run_cfme_updates(appliance_set, rh_updates_data, appliances_to_update)
    run_platform_updates(appliance_set, appliances_to_update)

try:
    skip_sat5_direct = not conf.cfme_data.redhat_updates.registration.sat5.test_direct
except KeyError:
    skip_sat5_direct = True


@pytest.mark.uncollectif(skip_sat5_direct,
    reason='RH Update test using Sat5 is not enabled')
@pytest.mark.long_running
def test_sat5_direct(appliance_set, rh_updates_data,
                     appliances_to_register, appliances_to_update):
    update_registration(appliance_set, rh_updates_data, 'sat5')
    register_appliances(appliance_set, appliances_to_register)

    download_repo_files(appliance_set, rh_updates_data, 'sat5', appliances_to_update)
    enable_repos(appliance_set, rh_updates_data, 'sat5', appliances_to_update)

    run_cfme_updates(appliance_set, rh_updates_data, appliances_to_update)
    run_platform_updates(appliance_set, appliances_to_update)

try:
    skip_sat6_direct = not conf.cfme_data.redhat_updates.registration.sat6.test_direct
except KeyError:
    skip_sat6_direct = True


@pytest.mark.uncollectif(skip_sat6_direct,
    reason='RH Update test using Sat6 is not enabled')
@pytest.mark.long_running
def test_sat6_direct(appliance_set, rh_updates_data,
                     appliances_to_register, appliances_to_update):
    update_registration(appliance_set, rh_updates_data, 'sat6')
    register_appliances(appliance_set, appliances_to_register)

    download_repo_files(appliance_set, rh_updates_data, 'rhn_mirror', appliances_to_update)
    enable_repos(appliance_set, rh_updates_data, 'rhn_mirror', appliances_to_update)

    run_cfme_updates(appliance_set, rh_updates_data, appliances_to_update)
    run_platform_updates(appliance_set, appliances_to_update)

try:
    skip_sat6_rhn_mirror = not conf.cfme_data.redhat_updates.registration.sat6.test_rhn_mirror
except KeyError:
    skip_sat6_rhn_mirror = True


@pytest.mark.uncollectif(skip_sat6_rhn_mirror,
    reason='RH Update test using Sat6/RHN Mirror is not enabled')
@pytest.mark.long_running
def test_sat6_rhn_mirror(appliance_set, rh_updates_data, appliances_to_update):
    # Use only primary to register_appliances(), download_repo_files() and enable_repos()
    target_appliances = [appliance_set.primary.name]

    update_registration(appliance_set, rh_updates_data, 'sat6')
    register_appliances(appliance_set, target_appliances)

    download_repo_files(appliance_set, rh_updates_data, 'rhn_mirror', target_appliances)
    enable_repos(appliance_set, rh_updates_data, 'rhn_mirror', target_appliances)
    rhn_mirror_setup(appliance_set)

    run_cfme_updates(appliance_set, rh_updates_data, appliances_to_update)
    run_platform_updates(appliance_set, appliances_to_update)
