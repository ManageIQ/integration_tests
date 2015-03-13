# -*- coding: utf-8 -*-

import pytest

from cfme.configure.configuration import set_server_roles
from cfme.configure import red_hat_updates
from copy import deepcopy
from utils import browser, conf, version
from utils.appliance import provision_appliance_set
from utils.log import logger
from utils.testgen import parametrize
from utils.wait import wait_for, TimedOutError

# Refresh interval used in wait_for
REFRESH_SEC = 15

"""
Used cfme_data.yaml section explained:
--------------------------------------

redhat_updates:
    http_proxy:
        url: 10.11.12.13:1234  # Address[:port] of proxy server
        credentials: http_proxy_creds
    streams:
        '1.3':  # Data are stream/version-specific; the key must be 'major.minor' (must be quoted)
            rhsm:
                versions_to_test:  # Versions to update from
                    - 1.2.3.4
                    - 1.2          # This will use trackerbot to choose latest image from the series
                url: subscription.rhn.redhat.com  # Server address (web UI field)
                use_http_proxy: False             # Set to True to use proxy server (reg. test only)
                enable_repo: cfme-repo-name       # Repository to subscribe to (web UI field)
                test_direct: True                 # Set to True to test regular, direct update
                test_rhn_mirror: True             # Set to True to test content proxy (RHN mirror)
                ssh_download_repo_files:  # Repository files to download after registration
                                          # but before updating
                    - "http://example.com/path/to/CFME.repo"  # URL of the repository to download
                ssh_enable_repos:  # Repositories to enable after downloading of repository files
                    - rhel-6-server-cfme-repo  # Name of the repository to enable
            sat5:
                versions_to_test:
                    - 1.2.3.4
                url: https://sat5.example.com/XMLRPC
                use_http_proxy: False
                add_channel: cfme-channel-name        # Channel to add (web UI field)
                organization: 2                       # Organization ID to use (web UI field)
                test_direct: False
                ssh_add_channels:  # Channels to add after registration but before updating (sat5)
                    - rhel-6-server-cfme-channel
            sat6:
                versions_to_test:
                    - 1.2.3.4
                url: https://sat6.example.com
                use_http_proxy: False
                enable_repo: cfme-repo-name
                test_direct: False
                test_rhn_mirror: False
            cli:
                versions_to_test:
                    - 1.2.3.4
                    - 1.2
                test_direct: False
                ssh_download_repo_files:
                    - "http://example.com/path/to/CFME.repo"
                ssh_enable_repos:
                    - rhel-6-server-cfme-repo
"""


def generate_update_tests(metafunc, reg_method):
    if 'appliance_set_data' not in metafunc.fixturenames:
        return

    # Load the original appliance set from 'appliance_provisioning' yaml section
    argnames = ['appliance_set_data']
    argvalues = []
    idlist = []
    try:
        appliance_set_data = conf.cfme_data.get('appliance_provisioning', {})['appliance_set']
    except KeyError:
        pytest.mark.uncollect(metafunc.function)
        return
    # And generate the same data with different versions, from 'redhat_updates' yaml section
    for ver in (rh_updates_data()[reg_method]['versions_to_test'] or []):
        ver = str(ver)  # Make sure its a string
        app_set_data_diff_ver = deepcopy(appliance_set_data)
        app_set_data_diff_ver['primary_appliance']['version'] = ver
        for sec_appliance in app_set_data_diff_ver['secondary_appliances']:
            sec_appliance['version'] = ver
        argvalues.append([app_set_data_diff_ver])
        idlist.append('from {}'.format(ver))
    parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.fixture(scope='module')
def rh_updates_data():
    stream = version.current_stream()
    return conf.cfme_data['redhat_updates']['streams'][stream]


@pytest.yield_fixture(scope='function')
def appliance_set(appliance_set_data):
    appliance_set = provision_appliance_set(
        appliance_set_data, 'test_rh_updates', configure_kwargs={'update_rhel': False})

    appliance_set.primary.ipapp.browser_steal = True

    with appliance_set.primary.ipapp:
        yield appliance_set

    # Unregister and destroy all
    for appliance in appliance_set:
        with appliance.ipapp.ssh_client() as ssh:
            ssh.run_command('subscription-manager remove --all')
            ssh.run_command('subscription-manager unregister')
        appliance.destroy()


def get_available_version(appliance):
    """Get available CFME update version on appliance (over SSH)
    """
    post_ver_cmd = 'yum list available cfme > /dev/null 2>&1 && yum list available cfme 2>&1'\
                   ' | grep cfme | sed "s/ \+/ /g" | cut -f 2 -d " " | cut -f 1 -d "-"'

    with appliance.ipapp.ssh_client() as ssh:
        status, output = ssh.run_command(post_ver_cmd)
        assert status == 0, "Couldn't get available version of CFME, got '{}'".format(output)
        output = output.strip()
        logger.info('Found available version of CFME: {}'.format(output))
        post_ver = version.LooseVersion(output)
    return post_ver


def download_and_check_rpm_sig(appliance, package_name):
    """Checks RPM package for PGP/GPG signature

    Returns: False if we will have to use --nogpgcheck during update, True otherwise
    """
    with appliance.ipapp.ssh_client() as ssh:
        ssh.run_command('yumdownloader --destdir /tmp {}'.format(package_name))
        status, output = ssh.run_command('rpm -K /tmp/{}*'.format(package_name))

    output = output.lower()
    # signed
    if 'pgp' in output or 'gpg' in output:
        # and we have the key
        if status == 0:
            appliance.ipapp.log.info(
                'The CFME package is signed and the key has been already imported')
            return True
        # and we dont have the key (yet?)
        else:
            appliance.ipapp.log.warning(
                'The CFME package is signed but the key has not been imported')
            return False
    # not signed
    else:
        appliance.ipapp.log.warning('The CFME package is not signed')
        return False


def update_registration(appliance_set, rh_updates_data, reg_method):
    reg_data = rh_updates_data[reg_method]

    # versions before 5.2.2.3 dont have repo management in the UI
    if appliance_set.primary.version < '5.2.2.3':
        repo_or_channel = None
    elif reg_method in ('rhsm', 'sat6'):
        repo_or_channel = reg_data.get('enable_repo', None)
    else:
        repo_or_channel = reg_data.get('add_channel', None)

    red_hat_updates.update_registration(
        service=reg_method,
        url=reg_data['url'],
        username=conf.credentials[reg_method]['username'],
        password=conf.credentials[reg_method]['password'],
        repo_name=repo_or_channel,
        organization=reg_data.get('organization', None)
    )


def register_appliances(appliance_set, appliances_to_register, soft_assert):
    red_hat_updates.register_appliances(*appliances_to_register)

    logger.info('Waiting for appliance statuses to change from Not registered')
    wait_for(red_hat_updates.are_registered,
             func_args=appliances_to_register,
             num_sec=400,
             delay=40,
             fail_func=lambda: red_hat_updates.register_appliances(*appliances_to_register))
    logger.info('Done')

    logger.info('Waiting for implicit update check after registration')
    # The update check doesnt have to find any available updates, but it still has to run
    # Try to re-register every minute (network issues)
    try:
        wait_for(red_hat_updates.checked_updates,
                 func_args=appliances_to_register,
                 num_sec=480,
                 delay=60,
                 fail_func=lambda: red_hat_updates.register_appliances(*appliances_to_register))
    except TimedOutError:
        soft_assert(False, 'Implicit update check failed (did not happen in time)')
        logger.error('Implicit update check failed')
    else:
        logger.info('Done')

    # And all registered appliances should be registered and subscribed
    soft_assert(red_hat_updates.are_registered(appliances_to_register),
        'Failed to register all specified appliances')
    # BZ 1148569 in 5.3 (stuck at Unsubscribed even though it is subscribed)
    soft_assert(red_hat_updates.are_subscribed(appliances_to_register),
        'Failed to subscribe all specified appliances')


def download_repo_files(appliance_set, rh_updates_data, reg_method, target_appliances):
    """Downloads repository files to appliances
    """
    download_repos = rh_updates_data[reg_method].get('ssh_download_repo_files') or []
    if not download_repos:
        return
    download_repos_str = "wget --no-check-certificate --directory-prefix=/etc/yum.repos.d/ {}"\
                         .format(' '.join(download_repos))

    for appliance_name in target_appliances:
        appliance = appliance_set.find_by_name(appliance_name)
        with appliance.ipapp.ssh_client() as ssh:
            status, output = ssh.run_command(download_repos_str)
            assert status == 0, 'Failed to download specified repository files on machine {}'\
                                .format(appliance.address)


def enable_repos(appliance_set, rh_updates_data, reg_method, target_appliances):
    """Enables repositories on appliances using ssh
    """
    enable_repos = rh_updates_data[reg_method].get('ssh_enable_repos') or []
    if not enable_repos:
        return
    enable_repos_str = 'yum-config-manager --enable {}'.format(' '.join(enable_repos))

    for appliance_name in target_appliances:
        appliance = appliance_set.find_by_name(appliance_name)
        with appliance.ipapp.ssh_client() as ssh:
            for repo_name in enable_repos:
                # Get first column from 'yum' using 'cut' and grep for repo with matching name
                is_repo_disabled_str = "yum repolist disabled 2>&1 | cut -f1 -d' ' | grep '{}'"\
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
    add_channels = rh_updates_data['sat5'].get('ssh_add_channels') or []
    if not add_channels:
        return
    # We must prepend the -c parameter to each channel and join them all with spaces inbetween
    add_channels = ' '.join(['-c ' + channel for channel in add_channels])

    reg_creds = conf.credentials['sat5']
    add_channels_str = 'rhn-channel -a {} -u {} -p {}'\
                       .format(add_channels, reg_creds['username'], reg_creds['password'])

    for appliance_name in appliances_to_update:
        appliance = appliance_set.find_by_name(appliance_name)
        with appliance.ipapp.ssh_client() as ssh:
            status, output = ssh.run_command(add_channels_str)
            assert status == 0, 'Failed to add specified channels on machine {}'\
                                .format(appliance.address)


def rhn_mirror_setup(appliance_set, soft_assert):
    """Sets up RHN mirror feature on primary appliance and checks secondary are subscribed
    """
    set_server_roles(rhn_mirror=True)
    appliance_set.primary.ipapp.restart_evm_service()

    with appliance_set.primary.ipapp.ssh_client() as ssh:
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
    appliance_set.primary.ipapp.wait_for_web_ui()
    logger.info('Done')

    # Check /etc/yum.repos.d/cfme-mirror.repo file exists on secondary appliances
    for appliance in appliance_set.secondary:
        with appliance.ipapp.ssh_client() as ssh:
            def repo_file_exists():
                status, output = ssh.run_command('ls /etc/yum.repos.d/cfme-mirror.repo')
                if status == 0:
                    return True
                return False

            logger.info('Waiting for repository files to be created on secondary appliances')
            wait_for(func=repo_file_exists, delay=REFRESH_SEC, num_sec=120)
            logger.info('Done')

    # And confirm that all appliances are subscribed
    browser.start()
    soft_assert(red_hat_updates.are_subscribed([app.name for app in appliance_set.secondary]),
        'Failed to subscribe all secondary appliances (secondary via proxy)')


def run_cfme_updates(appliance_set, rh_updates_data, soft_assert, cli_only=False):
    """Runs CFME update using web UI and CLI of primary appliance or only CLI

    Note:
        CFME 5.3.1+ will, on non-db appliances, apply platform updates along with cfme updates
    """
    # Wait for yum check-update to finish
    wait_for(lambda: ssh.run_command('pgrep yum')[0] == 1,
             num_sec=600,
             delay=60)

    post_ver = get_available_version(appliance_set.primary)
    all_ssh_clients = [app.ipapp.ssh_client() for app in appliance_set]

    if download_and_check_rpm_sig(appliance_set.primary, 'cfme') is False:
        logger.info('RPM signature check failed - disabling yum GPG check on all appliances')
        for ssh in all_ssh_clients:
            ssh.run_command("sed -i 's/gpgcheck.*/gpgcheck=0/g' /etc/yum.conf")
            # Sat5
            ssh.run_command("sed -i 's/gpgcheck.*/gpgcheck=0/g' "
                            "/etc/yum/pluginconf.d/rhnplugin.conf")

    # If 5.2 to 5.3: stop, update over SSH (+ scl-utils), migrate and start
    if version.current_stream() != version.get_stream(post_ver):
        # Stop all & wait for web UIs to go down
        for ssh in all_ssh_clients:
            ssh.run_in_background('service evmserverd stop')
        for app in appliance_set:
            app.ipapp.wait_for_web_ui(running=False)
        # Proceed with upgrade
        for ssh in all_ssh_clients:
            ssh.run_in_background('yum -y update scl-utils cfme')
        # Wait until yum is finished and check version afterwards
        for ssh in all_ssh_clients:
            wait_for(lambda: ssh.run_command('pgrep yum')[0] == 1,
                     num_sec=1800,
                     delay=60)
        # Stop all and wait for web UIs to go down
        for ssh in all_ssh_clients:
            ssh.run_in_background('service evmserverd stop')
        for app in appliance_set:
            app.ipapp.wait_for_web_ui(running=False)
        # Harden security and migrate all with internal DBs
        appliance_set.harden_security_post_upgrade()
        for app in appliance_set:
            if app.ipapp.is_db_internal:
                app.ipapp.migrate_db()

    # If 5.2 to 5.2 or 5.3 to 5.3: run the update
    else:
        # Update all appliances
        if not cli_only:
            red_hat_updates.update_appliances(*appliance_set.all_appliance_names)
        else:
            # 5.3 versions below 5.3.1 always update everything, even on DB appliances
            if appliance_set.primary.version.is_in_series('5.3')\
               and appliance_set.primary.version < '5.3.1':
                update_cmd = 'yum -y update'
            else:
                update_cmd = 'yum -y update scl-utils cfme'
            for ssh in all_ssh_clients:
                ssh.run_in_background(update_cmd)
        # Wait until yum update is running (on primary)
        with appliance_set.primary.ipapp.ssh_client() as ssh:
            wait_for(lambda: ssh.run_command('pgrep -f "yum -y update"')[0] == 0,
                     num_sec=120,
                     delay=30)
        # Wait until yum is finished
        for ssh in all_ssh_clients:
            wait_for(lambda: ssh.run_command('pgrep yum')[0] == 1,
                     num_sec=1800,
                     delay=60)

    # Start all
    for ssh in all_ssh_clients:
        ssh.run_in_background('service evmserverd start')

    # Wait for all UIs to be up
    for app in appliance_set:
        app.ipapp.wait_for_web_ui()

    if cli_only:
        # Unset cached versions and check current versions over SSH
        logger.info('Checking appliance versions over SSH (should be {} now)'.format(post_ver))
        for app in appliance_set:
            del app.version
            del app.ipapp.version
            soft_assert(app.version == post_ver,
                        "Versions {} and {} don't match".format(app.version, post_ver))
        logger.info('Done')
    else:
        # Check versions in the web UI
        version_match_args = [post_ver] + appliance_set.all_appliance_names
        browser.start()
        logger.info('Checking appliance versions in the web UI, after update')
        wait_for(red_hat_updates.versions_match,
                 func_args=version_match_args,
                 num_sec=180,
                 delay=REFRESH_SEC,
                 fail_func=red_hat_updates.refresh)
        logger.info('Done')


def run_platform_updates(appliance_set, cli_only=False):
    """Runs platform update using ssh and makes sure that the web UI is running afterwards
    """
    all_ssh_clients = [app.ipapp.ssh_client() for app in appliance_set]

    with appliance_set.primary.ipapp.ssh_client() as ssh:
        status, output = ssh.run_command('yum check-update')
        # 100 == there are packages available for update on this appliance
        if status != 100:
            logger.info("No platform updates available")
            return
        logger.info("Available updates found - running platform update")

    # Stop all and wait for web UIs to go down
    for ssh in all_ssh_clients:
        ssh.run_in_background('service evmserverd stop')
    for app in appliance_set:
        app.ipapp.wait_for_web_ui(running=False)

    # Proceed with platform updates
    for ssh in all_ssh_clients:
        ssh.run_in_background('yum -y update')

    # Wait until yum is finished on all
    for ssh in all_ssh_clients:
        wait_for(lambda: ssh.run_command('pgrep yum')[0] == 1,
                 num_sec=1800,
                 delay=60)

    # Check that there are no updates available anymore
    with appliance_set.primary.ipapp.ssh_client() as ssh:
        status, output = ssh.run_command('yum check-update')
        assert status == 0, "There still are packages available; the platform update has failed"

    # Start the evm services and wait for web UIs
    for ssh in all_ssh_clients:
        ssh.run_in_background('service evmserverd start')
    for app in appliance_set:
        app.ipapp.wait_for_web_ui()

    if not cli_only:
        # Check platform update availability in the web UI
        def check_updates_and_refresh():
            red_hat_updates.check_updates(*appliance_set.all_appliance_names)
            red_hat_updates.refresh()

        browser.start()
        logger.info("Waiting for platform update statuses to change")
        wait_for(red_hat_updates.platform_updates_available,
                 func_args=appliance_set.all_appliance_names,
                 num_sec=120,
                 delay=REFRESH_SEC,
                 fail_condition=True,
                 fail_func=check_updates_and_refresh)
        logger.info("Done")
