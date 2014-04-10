import os
import subprocess

import requests

from utils import async, conf, db, lazycache
from utils.browser import browser_session
from utils.path import scripts_path
from utils.providers import provider_factory
from utils.randomness import generate_random_string
from utils.ssh import SSHClient
from utils.wait import wait_for


class ApplianceException(Exception):
    pass


class Appliance(object):
    """Appliance represents an already provisioned cfme appliance vm

    Args:
        provider_name: Name of the provider this appliance is running under
        vm_name: Name of the VM this appliance is running as
    """

    _default_name = 'EVM'
    _internal_db = 'INTERNAL'

    def __init__(self, provider_name, vm_name):
        """Initializes a deployed appliance VM
        """
        self.name = Appliance._default_name
        self.db_address = None

        self._provider_name = provider_name
        self._vm_name = vm_name

    @property
    def _provider(self):
        """
        Note:
            Cannot be cached because provider object is unpickable.
        """
        return provider_factory(self._provider_name)

    @lazycache
    def address(self):
        def is_ip_available():
            try:
                return self._provider.get_ip_address(self._vm_name)
            except AttributeError:
                return False

        if self._address is None:
            ec, tc = wait_for(is_ip_available,
                              delay=5,
                              num_sec=30)
        return self.ec

    @lazycache
    def db_address(self):
        # returns the appliance address by default, methods that set up the internal
        # db should set db_address to something else when they do that
        return self.address

    @lazycache
    def db(self):
        # slightly crappy: anything that changes self.db_address should also del(self.db)
        return db.Db(self.db_address)

    def configure(self,
                  db_address=None,
                  name_to_set=None,
                  fix_ntp_clock=True,
                  patch_ajax_wait=True):
        """Configures appliance - database setup, rename, ntp sync, ajax wait patch

        Utility method to make things easier.

        Args:
            db_address: Address of external database if set, internal database if ``None``
                        (default ``None``)
            name_to_set: Name to set the appliance name to if not ``None`` (default ``None``)
            fix_ntp_clock: Fixes appliance time if ``True`` (default ``True``)
            patch_ajax_wait: Patches ajax wait code if ``True`` (default ``True``)

        """
        if fix_ntp_clock is True:
            self.fix_ntp_clock()
        if patch_ajax_wait is True:
            self.patch_ajax_wait()
        if db_address is None:
            self.enable_internal_db()
        else:
            self.enable_external_db(db_address)
        self.wait_for_web_ui()

        if name_to_set is not None and name_to_set != self.name:
            self.rename(name_to_set)
            self.restart_evm_service()
            self.wait_for_web_ui()

    def fix_ntp_clock(self):
        """Fixes appliance time using NTP sync
        """
        with self.ssh_client() as ssh:
            status, msg = ssh.run_command('ntpd -gq')
            if status != 0:
                raise ApplianceException('Failed to sync time (NTP) on {}\nError: {}'
                                         .format(self.address, msg))

    def patch_ajax_wait(self, undo=False):
        """Patches ajax wait code

        Args:
            undo: Will undo the ajax wait code patch if set to ``True``
        """
        script = scripts_path.join('patch_ajax_wait.py')
        args = [str(script), self.address]
        if undo:
            args.append('-R')
        with open(os.devnull, 'w') as f_devnull:
            subprocess.call(args, stdout=f_devnull)

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

    def browser_session(self):
        """Creates browser session connected to this appliance

        Returns: Browser session connected to this appliance.

        Usage:
            with appliance.browser_session() as browser:
                browser.do_stuff(TM)
        """
        return browser_session(base_url='https://' + self.address)

    def db_session(self):
        """Creates db session connected to db this appliance is connected to

        Returns: Creates db session connected to db this appliance is connected to.

        Usage:
            with appliance.db_session() as db:
                db.do_stuff(TM)
        """
        return self.db.session

    def enable_internal_db(self):
        """Enables internal database
        """
        script = scripts_path.join('enable_internal_db.py')
        args = [str(script), self.address]
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

    def rename(self, new_name):
        """Changes appliance name

        Args:
            new_name: Name to set

        Note:
            Database must be up and running and evm service must be (re)started afterwards
            for the name change to take effect.
        """
        with self.db_session():
            vmdb_config = db.get_yaml_config('vmdb', self.db)
            vmdb_config['server']['name'] = new_name
            db.set_yaml_config('vmdb', vmdb_config, self.address)
        self.name = new_name

    def restart_evm_service(self):
        """Restarts the ``evmserverd`` service on this appliance
        """
        with self.ssh_client() as ssh:
            status, msg = ssh.run_command('service evmserverd restart')
            if status != 0:
                raise ApplianceException('Failed to restart evmserverd service on {}\nError: {}'
                                         .format(self.address, msg))

    def wait_for_web_ui(self, timeout=600, running=True):
        """Waits for the web UI to be running / to not be running

        Args:
            timeout: Number of seconds to wait until timeout (default ``600``)
            running: Specifies if we wait for web UI to start or stop (default ``True``)
                     ``True`` == start, ``False`` == stop
        """
        wait_for(func=lambda: self.is_web_ui_running,
                 message='appliance.is_web_ui_running',
                 delay=10,
                 fail_condition=not running,
                 num_sec=timeout)

    def destroy(self):
        """Destroys the VM this appliance is running as
        """
        self._provider.delete_vm(self._vm_name)

    @property
    def is_db_enabled(self):
        if self.db_address is None:
            return False
        return True

    @property
    def is_db_internal(self):
        if self.db_address == Appliance._internal_db:
            return True
        return False

    @property
    def is_running(self):
        return self._provider.is_vm_running(self._vm_name)

    @property
    def is_web_ui_running(self):
        try:
            resp = requests.get("https://" + self.address, verify=False, timeout=20)
        except (requests.Timeout, requests.ConnectionError):
            return False

        if resp.status_code == 200 and 'CloudForms' in resp.content:
            return True
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


def provision_appliance(version, vm_name_prefix='cfme'):
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
        version_digits = ''.join([letter for letter in version if letter.isdigit()])
        return '{}_{}_{}'.format(vm_name_prefix, version_digits, generate_random_string())

    templates_by_version = conf.cfme_data['appliance_provisioning']['versions']
    provider_name = conf.cfme_data['appliance_provisioning']['provider']
    prov_data = conf.cfme_data['management_systems'][provider_name]

    provider = provider_factory(provider_name)
    vm_name = _generate_vm_name()

    try:
        template_name = templates_by_version[version]
    except KeyError:
        raise ApplianceException('No template found matching version {}'.format(version))

    deploy_args = {}
    deploy_args['vm_name'] = vm_name

    if prov_data['type'] == 'rhevm':
        deploy_args['cluster_name'] = prov_data['default_cluster']

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

    # --- Provisioning stage
    # Provisioning runs asynchronously, out of order; results are returned in order (crucial)
    prov_args = []
    for appliance_data in all_appliances_data:
        prov_args.append((appliance_data['version'], vm_name_prefix))

    try:
        # This can raise very cryptic exceptions
        with async.ResultsPool() as res_pool:
            res_pool.map_async(_provision_appliance_wrapped, prov_args)
    except:
        raise ApplianceException(
            'Failed to provision appliance set - error in provisioning stage\n'
            'Check cfme_data yaml for errors in template names and provider setup')

    provisioned_appliances = res_pool.results[0].get()
    # ---

    # --- Configuration stage
    appliance_set = ApplianceSet(provisioned_appliances[0], provisioned_appliances[1:])
    appliance_set.primary.configure(name_to_set=primary_data['name'])
    for i, appliance in enumerate(appliance_set.secondary):
        appliance.configure(db_address=appliance_set.primary.address,
                            name_to_set=secondary_data[i]['name'])
    # ---

    return appliance_set


def _provision_appliance_wrapped(args):
    """A wrapper to use for async provisioning

    Needed, because map_async only accepts a single iterable.

    Note:
        Must be defined in top level.
    """
    return provision_appliance(*args)
