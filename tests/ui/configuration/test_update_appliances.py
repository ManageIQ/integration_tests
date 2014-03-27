# -*- coding: utf-8 -*-

"""
@author: apagac@redhat.com
@author: jkrocil@redhat.com
"""

from utils import conf
from fixtures import navigation as nav
from utils.wait import wait_for, TimedOutError
import pytest
import utils.appliance

# Refresh interval used in wait_for
REFRESH_SEC = 15

pytestmark = [pytest.mark.usefixtures("maximized")]

"""
Used cfme_data.yaml section explained:
--------------------------------------

redhat_updates:
    current_version: 1.3.3  # Version to check against after update
    unregister: True        # Set to True to unregister appliances at the end (sat6 and rhsm only)
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
        name_primary:       # must match an appliance name from appliance_provisioning yaml section
            register: True  # Set to True to register the appliance
            update: True    # Set to True to update the appliance
        name_secondary_1:
            register: True
            update: True
        name_secondary_2:
            register: True
            update: False
    download_repo_files:  # Repository files to download after registration but before updating
        - url: http://example.com/path/to/CFME.repo  # URL of the repository to download
          reg_methods:  # List of registration methods this specific repo applies to
              - rhsm    # Can be one of: rhsm, sat5, sat6, rhn_mirror (special case)
    enable_repos:  # Repositories to enable after downloading of repository files
        - name: rhel-6-server-cfme-repo  # Name of the repository to enable
          reg_methods:
              - rhsm
              - sat5
    add_channels:  # Channels to add after registration but before updating (sat5 only)
        - rhel-6-server-cfme-channel
"""


def pytest_generate_tests(metafunc):
    """Parametrizes RH updates test according to config in cfme_data yaml

    Can generate following combinations:
      rhsm:
        test_direct: RHSM or RHSM + proxy
        test_rhn_mirror: RHN mirror (over RHSM) or RHN mirror (over RHSM + proxy)
      sat5:
        test_direct: Sat 5 or Sat 5 + proxy
      sat6:
        test_direct: Sat 6 or Sat 6 + proxy
        test_rhn_mirror: RHN mirror over Sat 6 or RHN mirror over Sat 6 + proxy
    """
    if metafunc.cls.__name__ != 'TestRedhatUpdates':
        return

    argnames = ('reg_method', 'test_proxy', 'test_rhn_mirror')
    argvalues = []
    ids = []

    reg_methods = ('rhsm', 'sat5', 'sat6')
    rh_updates_data = conf.cfme_data['redhat_updates']
    reg_data = rh_updates_data['registration']

    for reg_method in reg_methods:

        can_use_rhn_mirror = reg_method in ('rhsm', 'sat6')

        test_direct = reg_data[reg_method].get('test_direct', False)
        test_rhn_mirror = can_use_rhn_mirror and reg_data[reg_method].get('test_rhn_mirror', False)
        test_proxy = reg_data[reg_method].get('use_http_proxy', False)

        if test_direct and test_proxy:
            argvalues.append([reg_method, True, False])
            ids.append('{}-{}-{}'.format(reg_method, 'proxy_on', 'rhn_mirror_off'))
        elif test_direct:
            argvalues.append([reg_method, False, False])
            ids.append('{}-{}-{}'.format(reg_method, 'proxy_off', 'rhn_mirror_off'))

        if test_rhn_mirror and test_proxy:
            argvalues.append([reg_method, True, True])
            ids.append('{}-{}-{}'.format(reg_method, 'proxy_on', 'rhn_mirror_on'))
        elif test_rhn_mirror:
            argvalues.append([reg_method, False, True])
            ids.append('{}-{}-{}'.format(reg_method, 'proxy_off', 'rhn_mirror_on'))

    metafunc.parametrize(argnames, argvalues, ids=ids, scope="class")


def nav_to_server_settings_pg():
    conf_pg = nav.navigate('configuration', 'Configure', 'Configuration')
    server_settings_pg = conf_pg.click_on_settings()\
                                .click_on_current_server_tree_node()\
                                .click_on_server_tab()
    return server_settings_pg


def nav_to_rh_updates_pg():
    conf_pg = nav.navigate('configuration', 'Configure', 'Configuration')
    return conf_pg.click_on_redhat_updates()


@pytest.fixture(scope='module')
def redhat_updates(cfme_data):
    return cfme_data['redhat_updates']


@pytest.fixture(scope='module')
def appliances_to_register(redhat_updates):
    """Names of all appliances with 'register' key set to True
    """
    appliance_names = []
    for appliance_name, appliance_data in redhat_updates['appliances'].iteritems():
        if appliance_data.get('register', False):
            appliance_names.append(appliance_name)
    return appliance_names


@pytest.fixture(scope='module')
def appliances_to_update(redhat_updates):
    """Names of all appliances with 'update' key set to True
    """
    appliance_names = []
    for appliance_name, appliance_data in redhat_updates['appliances'].iteritems():
        if appliance_data.get('update', False):
            appliance_names.append(appliance_name)
    return appliance_names


@pytest.mark.usefixtures("reg_method", "test_proxy", "test_rhn_mirror")
class TestRedhatUpdates:
    """Tests RH updates using provisioned appliance set

    Prerequisites:
        - appliance_provisioning in cfme_data.yaml (see utils.appliance)
        - redhat_updates in cfme_data.yaml (see above)
    """

    @pytest.mark.skip_selenium
    def test_provision_appliances(self):
        appliance_set_data = conf.cfme_data['appliance_provisioning']['appliance_set']
        appliance_set = utils.appliance.provision_appliance_set(appliance_set_data, 'rh_updates')
        TestRedhatUpdates.appliance_set = appliance_set

    def test_edit_registration(self, redhat_updates, reg_method, test_proxy):
        """Edits registration form in the web UI
        """
        with self.appliance_set.primary.browser_session():
            rh_updates_pg = nav_to_rh_updates_pg()
            reg_data = redhat_updates['registration'][reg_method]
            if test_proxy:
                proxy = redhat_updates['registration']['http_proxy']
                proxy_creds = conf.credentials['http_proxy']
            else:
                proxy = None
                proxy_creds = {}

            if reg_method in ('rhsm', 'sat6'):
                repo_or_channel = reg_data.get('enable_repo', None)
            else:
                repo_or_channel = reg_data.get('add_channel', None)

            rh_updates_pg.edit_registration(url=reg_data['url'],
                                            credentials=conf.credentials[reg_method],
                                            service=reg_method,
                                            organization=reg_data.get('organization', None),
                                            proxy=proxy,
                                            proxy_creds=proxy_creds,
                                            repo_or_channel=repo_or_channel)
            registered_pg = rh_updates_pg.save()
            flash_message = "Customer Information successfully saved"
            assert registered_pg.flash.message == flash_message, registered_pg.flash.message

    def test_register_appliances(self, appliances_to_register, test_rhn_mirror):
        """Registers appliances

        Note:
            When testing RHN mirror feature, appliances_to_register are ignored and only
            the primary appliance is registered and subscribed.
        """
        if test_rhn_mirror:
            appliances_to_register = [self.appliance_set.primary.name]

        with self.appliance_set.primary.browser_session():
            rh_updates_pg = nav_to_rh_updates_pg()
            rh_updates_pg.select_appliances(appliances_to_register)
            rh_updates_pg.register()
            flash_message = "Registration has been initiated for the selected Servers"
            assert rh_updates_pg.flash.message == flash_message, rh_updates_pg.flash.message
            wait_for(rh_updates_pg.appliances_registered,
                     func_args=[appliances_to_register],
                     num_sec=120,
                     delay=REFRESH_SEC,
                     fail_func=rh_updates_pg.refresh_list)
            # Wait for first implicit check for updates after registration
            # The update check doesnt have to find any available updates, but it still has to run
            wait_for(rh_updates_pg.platform_updates_checked,
                     func_args=[appliances_to_register],
                     num_sec=180,
                     delay=REFRESH_SEC,
                     fail_func=rh_updates_pg.refresh_list)
            # And all registered appliances should be registered and subscribed
            assert rh_updates_pg.appliances_registered(appliances_to_register),\
                'Failed to register all specified appliances'
            assert rh_updates_pg.appliances_subscribed(appliances_to_register),\
                'Failed to subscribe all specified appliances'

    @pytest.mark.skip_selenium
    def test_download_repo_files(self, reg_method, redhat_updates, test_rhn_mirror,
                                 appliances_to_update):
        """Downloads repository files to appliances

        Note:
            Specified in yaml by registration methods: rhsm|sat5|sat6|rhn_mirror (special case)
        """
        download_repos = redhat_updates.get('download_repo_files') or []
        # If using RHN mirror feature, we target only the primary appliance
        if test_rhn_mirror:
            target_appliances = [self.appliance_set.primary.name]
            download_curr_method = [repo['url'] for repo in download_repos
                                    if 'rhn_mirror' in repo.get('reg_methods', [])]
        else:
            target_appliances = appliances_to_update
            download_curr_method = [repo['url'] for repo in download_repos
                                    if reg_method in repo.get('reg_methods', [])]

        if not download_curr_method:
            pytest.skip('No repository files to download')

        download_repos_str = "wget --no-check-certificate --directory-prefix=/etc/yum.repos.d/ {}"\
                             .format(' '.join(download_curr_method))

        for appliance_name in target_appliances:
            appliance = self.appliance_set.find_by_name(appliance_name)
            with appliance.ssh_client() as ssh_client:
                status, output = ssh_client.run_command(download_repos_str)
                assert status == 0, 'Failed to download specified repository files on machine {}'\
                                    .format(appliance.address)

    @pytest.mark.skip_selenium
    def test_enable_repos(self, reg_method, redhat_updates, test_rhn_mirror, appliances_to_update):
        """Enables repositories on appliances using ssh

        Note:
            If using RHN mirror feature, we target only the primary appliance.
        """
        enable_repos = redhat_updates.get('enable_repos') or []
        if test_rhn_mirror:
            target_appliances = [self.appliance_set.primary.name]
            enable_curr_method = [repo['name'] for repo in enable_repos
                                 if 'rhn_mirror' in repo.get('reg_methods', [])]
        else:
            target_appliances = appliances_to_update
            enable_curr_method = [repo['name'] for repo in enable_repos
                                 if reg_method in repo.get('reg_methods', [])]

        if not enable_curr_method:
            pytest.skip('No repository files to enable')

        enable_repos_str = 'yum-config-manager --enable {}'.format(' '.join(enable_curr_method))

        for appliance_name in target_appliances:
            appliance = self.appliance_set.find_by_name(appliance_name)
            with appliance.ssh_client() as ssh_client:
                for repo_name in enable_repos:
                    # Get first column from 'yum' using 'cut' and grep for repo with matching name
                    is_repo_disabled_str = "yum repolist disabled | cut -f1 -d' ' | grep '{}'"\
                                           .format(repo_name)
                    status, output = ssh_client.run_command(is_repo_disabled_str)
                    assert status == 0, 'Repo {} is not disabled on machine {}'\
                                        .format(repo_name, appliance.address)
                status, output = ssh_client.run_command(enable_repos_str)
                assert status == 0, 'Failed to enable specified repositories on machine {}'\
                                    .format(appliance.address)

    @pytest.mark.skip_selenium
    def test_add_channels(self, reg_method, redhat_updates, appliances_to_update):
        """Adds channels on appliances_to_update using ssh
        """
        if reg_method != 'sat5':
            pytest.skip('Channels can be added only when using Satellite 5')

        add_channels = redhat_updates.get('add_channels') or []
        if not add_channels:
            pytest.skip('No channels to add')

        # We must prepend the -c parameter to each channel and join them all with spaces inbetween
        add_channels = ' '.join(['-c ' + channel for channel in add_channels])

        reg_creds = conf.credentials['sat5']
        add_channels_str = 'rhn-channel -a {} -u {} -p {}'\
                           .format(add_channels, reg_creds['username'], reg_creds['password'])

        for appliance_name in appliances_to_update:
            appliance = self.appliance_set.find_by_name(appliance_name)
            with appliance.ssh_client() as ssh_client:
                status, output = ssh_client.run_command(add_channels_str)
                assert status == 0, 'Failed to add specified channels on machine {}'\
                                    .format(appliance.address)

    def test_rhn_mirror_setup(self, test_rhn_mirror):
        """Sets up RHN mirror feature on primary appliance
        """
        if not test_rhn_mirror:
            pytest.skip('RHN Mirror is disabled for this test')

        with self.appliance_set.primary.browser_session():
            server_settings_pg = nav_to_server_settings_pg()
            desired_roles = server_settings_pg.selected_server_role_names
            desired_roles.append('rhn_mirror')
            server_settings_pg.set_server_roles(desired_roles)

        self.appliance_set.primary.restart_evm_service()

        with self.appliance_set.primary.ssh_client() as ssh:
            def is_repotrack_running():
                status, output = ssh.run_command('pgrep repotrack')
                if status == 0:
                    return True
                return False

            # Wait for repotrack to start
            wait_for(func=is_repotrack_running, delay=REFRESH_SEC, num_sec=300)

            # Wait for repotrack to finish
            wait_for(func=is_repotrack_running, delay=REFRESH_SEC, fail_condition=True, num_sec=900)

            # Check that repo folder exists on primary and contains cfme-appliance pkg
            assert ssh.run_command('ls -m1 /repo/mirror | grep cfme-appliance')[0] == 0,\
                "/repo/mirror on {} doesn't exist or doesn't contain cfme-appliance pkg"\
                .format(self.appliance_set.primary.name)

        self.appliance_set.primary.wait_for_web_ui()

        # Check /etc/yum.repos.d/cfme-mirror.repo file exists on secondary appliances
        for appliance in self.appliance_set.secondary:
            with appliance.ssh_client() as ssh:
                def repo_file_exists():
                    status, output = ssh.run_command('ls /etc/yum.repos.d/cfme-mirror.repo')
                    if status == 0:
                        return True
                    return False

                wait_for(func=repo_file_exists, delay=REFRESH_SEC, num_sec=120)

        # And confirm that all appliances are subscribed
        with self.appliance_set.primary.browser_session():
            rh_updates_pg = nav_to_rh_updates_pg()
            assert rh_updates_pg.appliances_subscribed(),\
                'Failed to subscribe all appliances (secondary via proxy)'

    def test_run_cfme_updates(self, redhat_updates, appliances_to_update):
        """Runs CFME update on appliances_to_update using web UI of primary appliance

        Note:
            Just a heads up - CFME 5.3+ will, on non-db appliances, apply platform updates
            along with cfme updates.
        """
        with self.appliance_set.primary.browser_session() as browser:
            rh_updates_pg = nav_to_rh_updates_pg()
            rh_updates_pg.select_appliances(appliances_to_update)
            rh_updates_pg.apply_cfme_updates()
            flash_message = "Update has been initiated for the selected Servers"
            assert rh_updates_pg.flash.message == flash_message, rh_updates_pg.flash.message

            # If primary will be updated too
            if self.appliance_set.primary.name in appliances_to_update:
                # We need to wait for the web UI to go down and up again
                self.appliance_set.primary.wait_for_web_ui(timeout=120,
                                                           running=False)
                self.appliance_set.primary.wait_for_web_ui(timeout=540)
                # Navigate back to RH Updates page
                browser.refresh()
                rh_updates_pg = nav_to_rh_updates_pg()

            wait_for(rh_updates_pg.check_versions,
                     func_args=[appliances_to_update, redhat_updates['current_version']],
                     num_sec=660,
                     delay=REFRESH_SEC,
                     fail_func=rh_updates_pg.refresh_list)

    def test_run_platform_updates(self, appliances_to_update):
        """Runs platform update on appliances_to_update using ssh
        """
        with self.appliance_set.primary.browser_session() as browser:
            rh_updates_pg = nav_to_rh_updates_pg()

            primary_will_be_updated = False
            for appliance_name in appliances_to_update:
                appliance = self.appliance_set.find_by_name(appliance_name)
                with appliance.ssh_client() as ssh_client:
                    status, output = ssh_client.run_command('yum check-update')
                    # 100 == there are packages available for update on this appliance
                    if status != 100:
                        continue
                    if appliance_name == self.appliance_set.primary.name:
                        primary_will_be_updated = True
                    status, output = ssh_client.run_command('yum update -y &')
                    assert status == 0, 'Failed to start platform updates on machine {}'\
                                        .format(appliance.address, output)

            # If primary will be updated too
            if primary_will_be_updated:
                with self.appliance_set.primary.ssh_client() as ssh:
                    def is_yum_running():
                        status, output = ssh.run_command('pgrep yum')
                        if status == 0:
                            return True
                        return False

                    # Wait for yum to start
                    wait_for(func=is_yum_running, delay=REFRESH_SEC, num_sec=60)

                    # Wait for yum to finish
                    wait_for(func=is_yum_running,
                             delay=REFRESH_SEC,
                             fail_condition=True,
                             num_sec=900)

                    try:
                        # If updating is done and the web UI doesn't go down in 60sec
                        self.appliance_set.primary.wait_for_web_ui(timeout=60, running=False)
                    except TimedOutError:
                        # we can proceed, because it won't go down at all
                        pass
                    else:
                        # else, we will have to wait for it to come up again
                        self.appliance_set.primary.wait_for_web_ui(timeout=540)
                    # Navigate back to RH Updates page
                    browser.refresh()
                    rh_updates_pg = nav_to_rh_updates_pg()

            def check_updates_and_refresh():
                rh_updates_pg.select_appliances(appliances_to_update)
                rh_updates_pg.check_updates()
                rh_updates_pg.refresh_list()

            wait_for(rh_updates_pg.platform_updates_available,
                     func_args=[appliances_to_update],
                     num_sec=900,
                     delay=REFRESH_SEC,
                     fail_condition=True,
                     fail_func=check_updates_and_refresh)

    @pytest.mark.skip_selenium
    def test_unregister_appliances(self, reg_method, redhat_updates, appliances_to_register):
        """Unregisters appliances

        Note:
            Works only with rhsm and sat6 and only if set to True in cfme_data yaml.
        """
        if reg_method in ('rhsm', 'sat6') and redhat_updates.get('unregister', True):
            for appliance_name in appliances_to_register:
                appliance = self.appliance_set.find_by_name(appliance_name)
                with appliance.ssh_client() as ssh_client:
                    ssh_client.run_command('subscription-manager remove --all')
                    ssh_client.run_command('subscription-manager unregister')
        else:
            pytest.skip("Appliances not unregistered (either using sat5 or disabled)")

    @pytest.mark.skip_selenium
    def test_destroy_appliances(self):
        for appliance in self.appliance_set.all_appliances:
            appliance.destroy()
