import os
import subprocess
import requests
from requests.packages.urllib3.exceptions import ProtocolError
from time import sleep
from utils import conf, db, lazycache
from utils.browser import browser_session
from utils.log import logger
from utils.path import scripts_path
from utils.providers import provider_factory
from utils.randomness import generate_random_string
from utils.ssh import SSHClient
from utils.wait import wait_for
from utils.version import get_version, LATEST


class ApplianceException(Exception):
    pass


class Appliance(object):
    """Appliance represents an already provisioned cfme appliance vm

    Args:
        provider_name: Name of the provider this appliance is running under
        vm_name: Name of the VM this appliance is running as
    """

    _default_name = 'EVM'

    def __init__(self, provider_name, vm_name):
        """Initializes a deployed appliance VM
        """
        self.name = Appliance._default_name
        self.db_address = None

        self._provider_name = provider_name
        self.vmname = vm_name

    @lazycache
    def ipapp(self):
        return IPAppliance(self.address)

    @lazycache
    def provider(self):
        """
        Note:
            Cannot be cached because provider object is unpickable.
        """
        return provider_factory(self._provider_name)

    @property
    def vm_name(self):
        """ VM's name of the appliance on the provider """
        return self.vmname

    @lazycache
    def address(self):
        def is_ip_available():
            try:
                return self.provider.get_ip_address(self.vm_name)
            except AttributeError:
                return False

        ec, tc = wait_for(is_ip_available,
                          delay=5,
                          num_sec=30)
        return ec

    @lazycache
    def db_address(self):
        # returns the appliance address by default, methods that set up the internal
        # db should set db_address to something else when they do that
        return self.ipapp.address

    @lazycache
    def db(self):
        # slightly crappy: anything that changes self.db_address should also del(self.db)
        return self.ipapp.db

    @lazycache
    def version(self):
        return self.ipapp.version

    def _custom_configure(self, **kwargs):
        region = kwargs.get('region', 0)
        db_address = kwargs.get('db_address', None)
        if kwargs.get('fix_ntp_clock', True) is True:
            self.ipapp.fix_ntp_clock()
        if kwargs.get('patch_ajax_wait', True) is True:
            self.ipapp.patch_ajax_wait()
        if kwargs.get('db_address', None) is None:
            self.ipapp.enable_internal_db(region)
        else:
            self.ipapp.enable_external_db(db_address, region)
        self.ipapp.wait_for_db()
        if kwargs.get('loosen_pgssl', True) is True:
            self.ipapp.loosen_pgssl()

        name_to_set = kwargs.get('name_to_set', None)
        if name_to_set is not None and name_to_set != self.name:
            self.rename(name_to_set)
            self.ipapp.restart_evm_service()
            self.ipapp.wait_for_web_ui()

    def _configure_5_2(self):
        self.ipapp.update_rhel()
        self.ipapp.enable_internal_db()
        self.ipapp.wait_for_web_ui()
        self.ipapp.fix_ntp_clock()
        self.ipapp.deploy_merkyl()

    def _configure_5_3(self):
        self.ipapp.update_rhel()
        self.ipapp.enable_internal_db()
        self.ipapp.wait_for_web_ui()
        self.ipapp.precompile_assets()
        self.ipapp.loosen_pgssl()
        self.ipapp.clone_domain()
        self.ipapp.deploy_merkyl()

    def _configure_upstream(self):
        self.ipapp.wait_for_web_ui()
        self.ipapp.loosen_pgssl()
        self.ipapp.clone_domain()
        self.ipapp.deploy_merkyl()

    def configure(self, **kwargs):
        """Configures appliance - database setup, rename, ntp sync, ajax wait patch

        Utility method to make things easier.

        Args:
            db_address: Address of external database if set, internal database if ``None``
                        (default ``None``)
            name_to_set: Name to set the appliance name to if not ``None`` (default ``None``)
            region: Number to assign to region (default ``0``)
            fix_ntp_clock: Fixes appliance time if ``True`` (default ``True``)
            patch_ajax_wait: Patches ajax wait code if ``True`` (default ``True``)
            loosen_pgssl: Loosens postgres connections if ``True`` (default ``True``)

        """
        if kwargs:
            self._custom_configure(**kwargs)
        else:
            if self.version.is_in_series("5.2"):
                self._configure_5_2()
            elif self.version.is_in_series("5.3"):
                self._configure_5_3()
            elif self.version == LATEST:
                self._configure_upstream()

    def does_vm_exist(self):
        return self.provider.does_vm_exist(self.vm_name)

    def rename(self, new_name):
        """Changes appliance name

        Args:
            new_name: Name to set

        Note:
            Database must be up and running and evm service must be (re)started afterwards
            for the name change to take effect.
        """
        vmdb_config = db.get_yaml_config('vmdb', self.db)
        vmdb_config['server']['name'] = new_name
        db.set_yaml_config('vmdb', vmdb_config, self.address)
        self.name = new_name

    def destroy(self):
        """Destroys the VM this appliance is running as
        """
        self.provider.delete_vm(self.vm_name)

    @property
    def is_running(self):
        return self.provider.is_vm_running(self.vm_name)


class IPAppliance(object):
    """IPAppliance represents an already provisioned cfme appliance whos provider is unknown
    but who has an IP address. This has a lot of core functionality that Appliance uses, since
    it knows both the provider, vm_name and can there for derive the IP address.

    Args:
        ipaddress: The IP address of the provider
    """

    def __init__(self, ipaddress):
        self.address = ipaddress

    @lazycache
    def version(self):
        return get_version(self.ssh_client().get_version())

    def ssh_client(self, **connect_kwargs):
        """Creates ssh client (connected to this appliance by default)

        Args:
            **connect_kwargs: Keyword arguments accepted by the SSH client, including
                              ``username``, ``password``, and ``hostname``.


        Returns: A configured :py:class:`utils.ssh.SSHClient` instance.

        Usage:

            with appliance.ssh_client() as ssh:
                status, output = ssh.run_command('...')

        Note:

            The credentials default to those found under ``ssh`` key in ``credentials.yaml``.
        """
        connect_kwargs['hostname'] = connect_kwargs.get('hostname', self.address)

        return SSHClient(**connect_kwargs)

    def fix_ntp_clock(self):
        """Fixes appliance time using NTP sync
        """
        script = scripts_path.join('ntp_clock_set.py')
        args = [str(script), self.address]
        with open(os.devnull, 'w') as f_devnull:
            status = subprocess.call(args, stdout=f_devnull)
        if status != 0:
            raise ApplianceException('Appliance {} failed to set_clock'
                                     .format(self.address))

    def precompile_assets(self):
        """Precompile the assets"""
        script = scripts_path.join('precompile_assets.py')
        args = [str(script), self.address]
        with open(os.devnull, 'w') as f_devnull:
            status = subprocess.call(args, stdout=f_devnull)
        if status != 0:
            raise ApplianceException('Appliance {} failed to precompile assets'
                                     .format(self.address))

    def clone_domain(self, src="ManageIQ", dst="Default"):
        """Clones Automate domain

        Args:
            src: Source domain name.
            dst: Destination domain name.

        Note:
            Does nothing for versions below 5.3
        """
        if self.version < '5.3':
            return
        script = scripts_path.join('clone_domain.py')
        args = [str(script), self.address, src, dst]
        with open(os.devnull, 'w') as f_devnull:
            status = subprocess.call(args, stdout=f_devnull)
        if status != 0:
            raise ApplianceException('Appliance {} failed to clone the domain'
                                     .format(self.address))

    def deploy_merkyl(self):
        """Deploys Merkyl"""
        script = scripts_path.join('merkyl_deploy.py')
        args = [str(script), self.address]
        with open(os.devnull, 'w') as f_devnull:
            status = subprocess.call(args, stdout=f_devnull)
        if status != 0:
            raise ApplianceException('Appliance {} failed to deploy merkyl'
                                     .format(self.address))

    def update_rhel(self, url_or_urls=None, reboot=True):
        """Update RHEL on appliance"""
        script = scripts_path.join('update_rhel.py')
        args = [str(script), self.address]

        if reboot:
            args.append('--reboot')

        if not url_or_urls:
            url_or_urls = [conf.cfme_data['basic_info']['rhel_updates_url']]
            if self.version.is_in_series("5.3"):
                url_or_urls.append(conf.cfme_data['basic_info']['rhscl_updates_url'])

        if isinstance(url_or_urls, basestring):
            args += ['--url', url_or_urls]
        elif isinstance(url_or_urls, list):
            for url in url_or_urls:
                args += ['--url', url]

        with open(os.devnull, 'w') as f_devnull:
            status = subprocess.call(args, stdout=f_devnull)
        if status != 0:
            raise ApplianceException('Appliance {} failed to update RHEL'
                                     .format(self.address))

    def patch_ajax_wait(self, undo=False):
        """Patches ajax wait code

        Args:
            undo: Will undo the ajax wait code patch if set to ``True``

        Note:
            Does nothing for versions including and above 5.3
        """
        if self.version >= '5.3':
            return

        script = scripts_path.join('patch_ajax_wait.py')
        args = [str(script), self.address]
        if undo:
            args.append('-R')
        with open(os.devnull, 'w') as f_devnull:
            subprocess.call(args, stdout=f_devnull)

    def loosen_pgssl(self):
        """Loosens postgres connections

        Note:
            Does nothing for versions below 5.3
        """
        if self.version < '5.3':
            return

        script = scripts_path.join('loosen_pgssl_connections.py')
        args = [str(script), self.address]
        with open(os.devnull, 'w') as f_devnull:
            subprocess.call(args, stdout=f_devnull)

    def browser_session(self, reset_cache=False):
        """Creates browser session connected to this appliance

        Returns: Browser session connected to this appliance.

        Usage:
            with appliance.browser_session() as browser:
                browser.do_stuff(TM)
        """
        return browser_session(base_url='https://' + self.address, reset_cache=reset_cache)

    def enable_internal_db(self, region=0):
        """Enables internal database
        """
        logger.info('Enabling internal DB (region {}) on {}.'.format(region, self.address))
        self.db_address = self.address
        del(self.db)
        script = scripts_path.join('enable_internal_db.py')
        args = [str(script), self.address, '--region', str(region)]
        with open(os.devnull, 'w') as f_devnull:
            status = subprocess.call(args, stdout=f_devnull)
        if status != 0:
            raise ApplianceException('Appliance {} failed to enable internal DB'
                                     .format(self.address))

    def enable_external_db(self, db_address, region=0):
        """Enables external database

        Args:
            db_address: Address of the external database
            region: Number of region to join
        """
        logger.info('Enabling external DB (db_address {}, region {}) on {}.'
                    .format(db_address, region, self.address))
        # reset the db address and clear the cached db object if we have one
        self.db_address = db_address
        del(self.db)
        script = scripts_path.join('enable_external_db.py')
        args = [str(script), self.address, db_address, '--region', str(region)]
        with open(os.devnull, 'w') as f_devnull:
            status = subprocess.call(args, stdout=f_devnull)
        if status != 0:
            raise ApplianceException('Appliance {} failed to enable external DB running on {}'
                                     .format(self.address, db_address))

    def is_web_ui_running(self, unsure=False):
        """Triple checks if web UI is up and running

        Args:
            unsure: Variable to return when not sure if web UI is running or not
                    (default ``False``)

        Note:
            Waits/sleeps for 3 seconds inbetween checks.
        """
        num_of_tries = 3
        was_running_count = 0
        for try_num in range(num_of_tries):
            try:
                resp = requests.get("https://" + self.address, verify=False, timeout=15)
                if resp.status_code == 200 and 'Dashboard' in resp.content:
                    was_running_count += 1
            except (requests.Timeout, requests.ConnectionError, ProtocolError):
                # wasn't running
                pass
            if try_num < (num_of_tries - 1):
                sleep(3)

        if was_running_count == 0:
            return False
        elif was_running_count == num_of_tries:
            return True
        else:
            return unsure

    def restart_evm_service(self):
        """Restarts the ``evmserverd`` service on this appliance
        """
        with self.ssh_client() as ssh:
            status, msg = ssh.run_command('service evmserverd restart')
            if status != 0:
                raise ApplianceException('Failed to restart evmserverd service on {}\nError: {}'
                                         .format(self.address, msg))

    def wait_for_web_ui(self, timeout=900, running=True):
        """Waits for the web UI to be running / to not be running

        Args:
            timeout: Number of seconds to wait until timeout (default ``600``)
            running: Specifies if we wait for web UI to start or stop (default ``True``)
                     ``True`` == start, ``False`` == stop
        """
        wait_for(func=lambda unsure: self.is_web_ui_running(unsure),
                 func_args=[not running],
                 message='appliance.is_web_ui_running',
                 delay=10,
                 fail_condition=not running,
                 num_sec=timeout)

    def wait_for_db(self, timeout=180):
        """Waits for appliance database to be ready

        Args:
            timeout: Number of seconds to wait until timeout (default ``180``)
        """
        wait_for(func=lambda: self.is_db_ready,
                 message='appliance.is_db_ready',
                 delay=20,
                 numsec=timeout)

    @lazycache
    def db_address(self):
        # returns the appliance address by default, methods that set up the internal
        # db should set db_address to something else when they do that
        return self.address

    @lazycache
    def db(self):
        # slightly crappy: anything that changes self.db_address should also del(self.db)
        return db.Db(self.db_address)

    @property
    def is_db_enabled(self):
        if self.db_address is None:
            return False
        return True

    @property
    def is_db_internal(self):
        if self.db_address == self.address:
            return True
        return False

    @property
    def is_db_ready(self):
        if self.is_db_internal:
            ssh_cl = self.ssh_client()
        else:
            ssh_cl = SSHClient(hostname=self.db_address)
        ec, out = ssh_cl.run_command('psql -U postgres -t  -c "select now()" postgres')
        if ec == 0:
            return True
        else:
            return False


class ApplianceSet(object):
    """Convenience class to ease access to appliances in appliance_set
    """
    def __init__(self, primary_appliance=None, secondary_appliances=None):
        self.primary = primary_appliance
        self.secondary = secondary_appliances or list()

    @property
    def all_appliances(self):
        all_appliances = self.secondary[:]
        all_appliances.append(self.primary)
        return all_appliances

    def find_by_name(self, appliance_name):
        """Finds appliance of given name

        Returns: Instance of :py:class:`Appliance` if found, ``None`` otherwise
        """
        for appliance in self.all_appliances:
            if appliance.name == appliance_name:
                return appliance
        return None


def provision_appliance(version=None, vm_name_prefix='cfme', template=None, provider_name=None,
                        vm_name=None):
    """Provisions fresh, unconfigured appliance of a specific version

    Note:
        Version must be mapped to template name under ``appliance_provisioning > versions``
        in ``cfme_data.yaml``.

    Args:
        version: version of appliance to provision
        vm_name_prefix: name prefix to use when deploying the appliance vm

    Returns: Unconfigured appliance; instance of :py:class:`Appliance`

    Usage:
        my_appliance = provision_appliance('5.2.1.8', 'my_tests')
        my_appliance.fix_ntp_clock()
        my_appliance.enable_internal_db()
        my_appliance.wait_for_web_ui()
        or
        my_appliance = provision_appliance('5.2.1.8', 'my_tests')
        my_appliance.configure(patch_ajax_wait=False)
        (identical outcome)
    """

    def _generate_vm_name():
        if version is not None:
            version_digits = ''.join([letter for letter in version if letter.isdigit()])
            return '{}_{}_{}'.format(vm_name_prefix, version_digits, generate_random_string())
        else:
            return '{}_{}'.format(vm_name_prefix, generate_random_string())

    if version is not None:
        templates_by_version = conf.cfme_data['appliance_provisioning']['versions']
        try:
            template_name = templates_by_version[version]
        except KeyError:
            raise ApplianceException('No template found matching version {}'.format(version))

    if template is not None:
        template_name = template

    if provider_name is None:
        provider_name = conf.cfme_data['appliance_provisioning']['default_provider']
    prov_data = conf.cfme_data['management_systems'][provider_name]

    provider = provider_factory(provider_name)
    if not vm_name:
        vm_name = _generate_vm_name()

    deploy_args = {}
    deploy_args['vm_name'] = vm_name

    if prov_data['type'] == 'rhevm':
        deploy_args['cluster'] = prov_data['default_cluster']

    provider.deploy_template(template_name, **deploy_args)

    return Appliance(provider_name, vm_name)


def provision_appliance_set(appliance_set_data, vm_name_prefix='cfme'):
    """Provisions configured appliance set according to appliance_set_data dict

    This provides complete working appliance set - with DBs enabled and names set.

    Primary appliance will have internal database enabled and secondary appliances
    will be connected to the database on primary.

    Args:
        vm_name_prefix: name prefix to use when deploying the appliance vms
        appliance_set_data: dict that corresponds to the following yaml structure:

    .. code-block:: yaml

        primary_appliance:
            name: name_primary
            version: 1.3.3
        secondary_appliances:
            - name: name_secondary_1
              version: 1.2.3
            - name: name_secondary_2
              version: 1.3.3

    Warning:
        Secondary appliances must be of the same or lower version than the primary one.
        Otherwise, there is a risk that the secondary of higher version will try to
        migrate the primary's database (and fail at it).

    Returns: Configured appliance set; instance of :py:class:`ApplianceSet`
    """

    primary_data = appliance_set_data['primary_appliance']
    secondary_data = appliance_set_data.get('secondary_appliances') or []
    all_appliances_data = [primary_data] + secondary_data

    logger.info('Provisioning appliances')
    provisioned_appliances = []
    try:
        for appliance_data in all_appliances_data:
            app = provision_appliance(appliance_data['version'], vm_name_prefix)
            provisioned_appliances.append(app)
    except:
        raise ApplianceException(
            'Failed to provision appliance set - error in provisioning stage\n'
            'Check cfme_data yaml for errors in template names and provider setup'
        )
    appliance_set = ApplianceSet(provisioned_appliances[0], provisioned_appliances[1:])
    logger.info('Done - provisioning appliances')

    logger.info('Configuring appliances')
    appliance_set.primary.configure(name_to_set=primary_data['name'])
    for i, appliance in enumerate(appliance_set.secondary):
        appliance.configure(db_address=appliance_set.primary.address,
                            name_to_set=secondary_data[i]['name'])
    logger.info('Done - configuring appliances')

    return appliance_set
