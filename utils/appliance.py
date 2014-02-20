from utils import conf
from utils import path as utils_path
from utils.browser import browser_session
from utils.cfmedb import get_yaml_config, set_yaml_config
from utils.providers import provider_factory
from utils.randomness import generate_random_string
from utils.ssh import SSHClient
from utils.wait import wait_for
import requests
import subprocess


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

        self._provider = provider_factory(provider_name)
        self._vm_name = vm_name
        self._address = None

    @property
    def address(self):
        if self._address is None:
            self._address = self._provider.get_ip_address(self._vm_name)
        return self._address

    def fix_ntp_clock(self):
        """Fixes appliance time using NTP sync
        """
        with self.ssh_client() as ssh:
            status, msg = ssh.run_command('ntpd -gq')
            if status != 0:
                raise Exception('Failed to sync time (NTP) on {}\nError: {}'
                                .format(self.address, msg))

    def patch_ajax_wait(self, undo=False):
        """Patches ajax wait code

        Args:
            undo: Will undo the ajax wait code patch if set to ``True``
        """
        script = utils_path.scripts_path.join('patch_ajax_wait.py')
        args = [str(script), self.address]
        if undo:
            args.append('-R')
        status = subprocess.call(args)
        if status != 0:
            raise Exception('Failed to patch ajax wait code on {}'
                            .format(self.address))

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

    def enable_internal_db(self):
        """Enables internal database
        """
        self.db_address = Appliance._internal_db
        script = utils_path.scripts_path.join('enable_internal_db.py')
        args = [str(script), self.address]
        status = subprocess.call(args)
        if status != 0:
            raise Exception('Appliance {} failed to enable internal DB'.format(self.address))

    def enable_external_db(self, db_address):
        """Enables external database

        Args:
            db_address: Address of the external database
        """
        self.db_address = db_address
        script = utils_path.scripts_path.join('enable_external_db.py')
        args = [str(script), self.address, db_address]
        status = subprocess.call(args)
        if status != 0:
            raise Exception('Appliance {} failed to enable external DB running on {}'
                            .format(self.address, db_address))

    def rename(self, new_name):
        """Changes appliance name

        Args:
            new_name: Name to set
        """
        vmdb_config = get_yaml_config('vmdb')
        vmdb_config['server']['name'] = new_name
        set_yaml_config('vmdb', vmdb_config)

    def restart_evm_service(self):
        """Restarts the ``evmserverd`` service on this appliance
        """
        with self.ssh_client() as ssh:
            status, msg = ssh.run_command('service evmserverd restart')
            if status != 0:
                raise Exception('Failed to restart evmserverd service on {}\nError: {}'
                                .format(self.address, msg))

    def wait_for_web_ui(self, timeout=600):
        """Waits for the web UI to start

        Args:
            timeout: Number of seconds to wait until timeout
        """
        wait_for(func=lambda: self.is_web_ui_running,
                 message='appliance.is_web_ui_running',
                 delay=10,
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
            resp = requests.get("https://" + self.address, verify=False, timeout=5)
        except (requests.Timeout, requests.ConnectionError):
            return False

        if resp.status_code == 200 and 'CloudForms' in resp.content:
            return True
        return False


class ApplianceSet(object):
    """Convenience class to ease access to appliances in appliance_set
    """
    def __init__(self):
        self.primary = None
        self.secondary = []

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
        ...
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
        raise Exception('No template found matching version {}'.format(version))

    deploy_args = {}
    deploy_args['vm_name'] = vm_name

    if prov_data['type'] == 'rhevm':
        deploy_args['cluster_name'] = prov_data['default_cluster']

    provider.deploy_template(template_name, **deploy_args)

    return Appliance(provider_name, vm_name)


def provision_appliance_set(appliance_set_data, vm_name_prefix='cfme'):
    """Provisions appliance set according to appliance_set_data dict

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

    Returns: Configured appliance set; instance of :py:class:`ApplianceSet`
    """

    primary_data = appliance_set_data['primary_appliance']
    secondary_data = appliance_set_data['secondary_appliances']

    appliance_set = ApplianceSet()

    appliance_set.primary = provision_appliance(primary_data['version'], vm_name_prefix)
    appliance_set.primary.fix_ntp_clock()
    appliance_set.primary.patch_ajax_wait()
    appliance_set.primary.enable_internal_db()
    appliance_set.primary.wait_for_web_ui()
    appliance_set.primary.rename(primary_data['name'])

    for appliance_data in secondary_data:
        appliance = provision_appliance(appliance_data['version'], vm_name_prefix)
        appliance_set.primary.fix_ntp_clock()
        appliance_set.primary.patch_ajax_wait()
        appliance.enable_external_db(appliance_set.primary.address)
        appliance.wait_for_web_ui()
        appliance.rename(appliance_data['name'])
        appliance_set.secondary.append(appliance)

    return appliance_set
