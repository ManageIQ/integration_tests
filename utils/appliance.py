# -*- coding: utf-8 -*-
import atexit
import os
import random
import shutil
import subprocess
from multiprocessing import Process
from tempfile import mkdtemp
from textwrap import dedent
from time import sleep
from urlparse import urlparse

import requests

from cfme.configure.configuration import server_name, server_id
from cfme.infrastructure.provider import get_from_config
from cfme.infrastructure.virtual_machines import Vm
from fixtures import ui_coverage
from fixtures.pytest_store import _push_appliance, _pop_appliance, store
from utils import api, conf, datafile, db, lazycache, trackerbot, db_queries
from utils.log import logger, create_sublogger
from utils.mgmt_system import RHEVMSystem, VMWareSystem
from utils.net import net_check
from utils.path import data_path, scripts_path
from utils.providers import provider_factory
from utils.randomness import generate_random_string
from utils.ssh import SSHClient
from utils.version import get_stream, get_version, LATEST
from utils.wait import wait_for


# Do not import the whole stuff around
if os.environ.get("RUNNING_UNDER_SPROUT", "false") == "false":
    from cfme.configure.configuration import set_server_roles, get_server_roles
    from utils.providers import setup_provider
    from utils.browser import browser_session
    from utils.hosts import setup_providers_hosts_credentials


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
    def rest_api(self):
        return self.ipapp.rest_api

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
                ip = self.provider.get_ip_address(self.vm_name)
                if ip is None:
                    return False
                else:
                    return ip
            except AttributeError:
                return False

        ec, tc = wait_for(is_ip_available,
                          delay=5,
                          num_sec=600)
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
        log_callback = kwargs.pop(
            "log_callback",
            lambda msg: logger.info("Custom configure {}: {}".format(self.vmname, msg)))
        region = kwargs.get('region', 0)
        db_address = kwargs.get('db_address', None)
        key_address = kwargs.get('key_address', None)
        db_username = kwargs.get('db_username', None)
        db_password = kwargs.get('ssh_password', None)
        ssh_password = kwargs.get('ssh_password', None)
        db_name = kwargs.get('db_name', None)

        if kwargs.get('fix_ntp_clock', True) is True:
            self.ipapp.fix_ntp_clock(log_callback=log_callback)
        if kwargs.get('patch_ajax_wait', True) is True:
            self.ipapp.patch_ajax_wait(log_callback=log_callback)
        if kwargs.get('db_address', None) is None:
            self.ipapp.enable_internal_db(
                region, key_address, db_password, ssh_password, log_callback=log_callback)
        else:
            self.ipapp.enable_external_db(
                db_address, region, db_name, db_username, db_password, log_callback=log_callback)
        self.ipapp.wait_for_web_ui(timeout=1800, log_callback=log_callback)
        if kwargs.get('loosen_pgssl', True) is True:
            self.ipapp.loosen_pgssl(log_callback=log_callback)

        name_to_set = kwargs.get('name_to_set', None)
        if name_to_set is not None and name_to_set != self.name:
            self.rename(name_to_set)
            self.ipapp.restart_evm_service(log_callback=log_callback)
            self.ipapp.wait_for_web_ui(log_callback=log_callback)

    def _configure_5_2(self, log_callback=None):
        self.ipapp.deploy_merkyl(start=True, log_callback=log_callback)
        self.ipapp.fix_ntp_clock(log_callback=log_callback)
        self.ipapp.enable_internal_db(log_callback=log_callback)
        self.ipapp.update_rhel(log_callback=log_callback)
        self.ipapp.wait_for_web_ui(timeout=1800, log_callback=log_callback)

    def _configure_5_3(self, log_callback=None):
        self.ipapp.deploy_merkyl(start=True, log_callback=log_callback)
        self.ipapp.fix_ntp_clock(log_callback=log_callback)
        self.ipapp.enable_internal_db(log_callback=log_callback)
        self.ipapp.loosen_pgssl(log_callback=log_callback)
        # need the web_ui to come up to ensure the DB is set up
        # before closing the automate domain
        self.ipapp.wait_for_web_ui(timeout=1800, log_callback=log_callback)
        self.ipapp.clone_domain(log_callback=log_callback)
        self.ipapp.update_rhel(log_callback=log_callback)
        self.ipapp.wait_for_web_ui(timeout=1800, log_callback=log_callback)

    def _configure_5_4(self, log_callback=None):
        # Patch the environment if needed
        self.ipapp.workaround_missing_gemfile(log_callback=log_callback)
        self._configure_5_3(log_callback=log_callback)

    def _configure_upstream(self, log_callback=None):
        self.ipapp.deploy_merkyl(start=True, log_callback=log_callback)
        self.ipapp.fix_ntp_clock(log_callback=log_callback)
        self.ipapp.setup_upstream_db(log_callback=log_callback)
        self.ipapp.wait_for_web_ui(timeout=1800, log_callback=log_callback)
        self.ipapp.loosen_pgssl(log_callback=log_callback)
        self.ipapp.clone_domain(log_callback=log_callback)

    def configure(self, setup_fleece=False, log_callback=None, **kwargs):
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
            key_address: Fetch encryption key from this address if set, generate a new key if
                         ``None`` (default ``None``)

        """
        if log_callback is None:
            log_callback = lambda message: logger.info("Appliance {} configure: {}".format(
                self.vmname,
                message.strip()
            ))
        self.ipapp.wait_for_ssh()
        if kwargs:
            self._custom_configure(**kwargs)
        else:
            if self.version.is_in_series("5.2"):
                self._configure_5_2(log_callback=log_callback)
            elif self.version.is_in_series("5.3"):
                self._configure_5_3(log_callback=log_callback)
            elif self.version.is_in_series("5.4"):
                self._configure_5_4(log_callback=log_callback)
            elif self.version == LATEST:
                self._configure_upstream(log_callback=log_callback)
        if setup_fleece:
            self.configure_fleecing(log_callback=log_callback)

    def configure_fleecing(self, log_callback=None):
        if log_callback is None:
            log_callback = lambda message: logger.info("Configure fleecing: {}".format(message))
        else:
            cb = log_callback
            log_callback = lambda message: cb("Configure fleecing: {}".format(message))

        if self.is_on_vsphere:
            self.ipapp.install_vddk(reboot=True, log_callback=log_callback)
            self.ipapp.wait_for_web_ui(log_callback=log_callback)

        if self.is_on_rhev:
            self.add_rhev_direct_lun_disk()

        self.ipapp.browser_steal = True
        with self.ipapp:
            log_callback('Enabling smart proxy role...')
            roles = get_server_roles()
            if not roles["smartproxy"]:
                roles["smartproxy"] = True
                set_server_roles(**roles)
                ver_list = str(self.version).split(".")
                if ver_list[0] is "5" and ver_list[1] is "2" and int(ver_list[3]) > 5:
                    sleep(600)

            # add provider
            log_callback('Setting up provider...')
            setup_provider(self._provider_name)

            # credential hosts
            log_callback('Credentialing hosts...')
            setup_providers_hosts_credentials(self._provider_name, ignore_errors=True)

            # if rhev, set relationship
            if self.is_on_rhev:
                vm = Vm(self.vm_name, get_from_config(self._provider_name))
                cfme_rel = Vm.CfmeRelationship(vm)
                cfme_rel.set_relationship(str(server_name()), server_id())

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
        if isinstance(self.provider, RHEVMSystem):
            # if rhev, try to remove direct_lun just in case it is detach
            self.remove_rhev_direct_lun_disk()
        self.provider.delete_vm(self.vm_name)

    @property
    def is_running(self):
        return self.provider.is_vm_running(self.vm_name)

    def browser_session(self):
        return self.ipapp.browser_session()

    @property
    def is_on_rhev(self):
        return isinstance(self.provider, RHEVMSystem)

    @property
    def is_on_vsphere(self):
        return isinstance(self.provider, VMWareSystem)

    def add_rhev_direct_lun_disk(self, log_callback=None):
        if log_callback is None:
            log_callback = logger.info
        if not self.is_on_rhev:
            log_callback("appliance NOT on rhev, unable to connect direct_lun")
            raise ApplianceException("appliance NOT on rhev, unable to connect direct_lun")
        log_callback('Adding RHEV direct_lun hook...')
        self.ipapp.wait_for_ssh()
        script = scripts_path.join('connect_directlun.py')
        args = [str(script), '--provider', self._provider_name, '--vm_name', self.vm_name]
        with open(os.devnull, 'w') as f_devnull:
            status = subprocess.call(args, stdout=f_devnull)
        if status != 0:
            msg = 'Appliance {} failed to connect rhev direct lun!'.format(self.address)
            log_callback(msg)
            raise ApplianceException(msg)

    def remove_rhev_direct_lun_disk(self, log_callback=None):
        if log_callback is None:
            log_callback = logger.info
        if not self.is_on_rhev:
            msg = "appliance {} NOT on rhev, unable to disconnect direct_lun".format(self.vmname)
            log_callback(msg)
            raise ApplianceException(msg)
        log_callback('Removing RHEV direct_lun hook...')
        self.ipapp.wait_for_ssh()
        script = scripts_path.join('connect_directlun.py')
        args = [str(script), '--remove', '--provider',
                self._provider_name, '--vm_name', self.vm_name]
        with open(os.devnull, 'w') as f_devnull:
            status = subprocess.call(args, stdout=f_devnull)
        if status != 0:
            msg = 'Appliance {} failed to disconnect rhev direct lun!'.format(self.address)
            log_callback(msg)
            raise ApplianceException(msg)


class IPAppliance(object):
    """IPAppliance represents an already provisioned cfme appliance whos provider is unknown
    but who has an IP address. This has a lot of core functionality that Appliance uses, since
    it knows both the provider, vm_name and can there for derive the IP address.

    Args:
        ipaddress: The IP address of the provider
        browser_streal: If True then then current browser is killed and the new appliance
            is used to generate a new session.
    """

    def __init__(self, address=None, browser_steal=False):
        if address is not None:
            self.address = address
        self.browser_steal = browser_steal
        # thing-toucher process, used for UI coverage
        self._thing_toucher_proc = None

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, repr(self.address))

    def push(self):
        _push_appliance(self)

    def pop(self):
        _pop_appliance(self)

    def __enter__(self):
        """ This method will replace the current appliance in the store """
        self.push()
        return self

    def __exit__(self, *args, **kwargs):
        self.pop()

    @property
    def managed_providers(self):
        """Returns a set of providers that are managed by this appliance

        Returns:
            :py:class:`set` of :py:class:`str` - provider_key-s
        """
        ems_table = self.db["ext_management_systems"]
        ip_addresses = set([])
        for ems in self.db.session.query(ems_table):
            ip_addresses.add(ems.ipaddress)
        provider_keys = set([])
        for provider_key, provider_data in conf.cfme_data.get("management_systems", {}).iteritems():
            if provider_data.get("ipaddress", None) in ip_addresses:
                provider_keys.add(provider_key)
        return provider_keys

    @classmethod
    def from_url(ip_appliance_class, url):
        # Need to think about this bit
        if url is None:
            url = conf.env['base_url']
        parsed_url = urlparse(url)
        ip_a = ip_appliance_class(parsed_url.hostname)
        # stash the passed-in url in the lazycache to save a step
        ip_a.url = url
        return ip_a

    @lazycache
    def rest_api(self):
        return api.API("https://{}/api".format(self.address), auth=("admin", "smartvm"))

    @lazycache
    def address(self):
        # If address wasn't set in __init__, use the hostname from base_url
        parsed_url = urlparse(store.base_url)
        return parsed_url.netloc

    @lazycache
    def url(self):
        return 'https://%s/' % self.address

    @lazycache
    def version(self):
        return get_version(self.ssh_client().get_version())

    @lazycache
    def log(self):
        return create_sublogger(self.address)

    def ssh_client(self, **connect_kwargs):
        """Creates an ssh client connected to this appliance

        Args:
            **connect_kwargs: Keyword arguments accepted by the SSH client

        Returns: A configured :py:class:`utils.ssh.SSHClient` instance.

        Usage:

            with appliance.ssh_client() as ssh:
                status, output = ssh.run_command('...')

        Note:

            The credentials default to those found under ``ssh`` key in ``credentials.yaml``.

        """
        if not self.is_ssh_running:
            raise Exception('SSH is unavailable')
        # IPAppliance.ssh_client only connects to its address
        connect_kwargs['hostname'] = self.address
        connect_kwargs['username'] = connect_kwargs.get(
            'username', conf.credentials['ssh']['username'])
        connect_kwargs['password'] = connect_kwargs.get(
            'password', conf.credentials['ssh']['password'])
        return SSHClient(**connect_kwargs)

    def db_ssh_client(self, **connect_kwargs):
        if self.is_db_internal:
            return self.ssh_client()
        else:
            return self.ssh_client()(hostname=self.db_address)

    def diagnose_evm_failure(self):
        """Go through various EVM processes, trying to figure out what fails

        Returns: A string describing the error, or None if no errors occurred.

        This is intended to be run after an appliance is configured but failed for some reason,
        such as in the template tester.

        """
        logger.info('Diagnosing EVM failures, this can take a while...')

        if not self.address:
            return 'appliance has no IP Address; provisioning failed or networking is broken'

        logger.info('Checking appliance SSH Connection')
        if not self.is_ssh_running:
            return 'SSH is not running on the appliance'

        # Now for the DB
        logger.info('Checking appliance database')
        if not self.db_online:
            # postgres isn't running, try to start it
            result = self.db_ssh_client().run_command('service postgresql92-postgresql restart')
            if result.rc != 0:
                return 'postgres failed to start:\n{}'.format(result.output)
            else:
                return 'postgres was not running for unknown reasons'

        if not self.db_has_database:
            return 'vmdb_production database does not exist'

        if not self.db_has_tables:
            return 'vmdb_production has no tables'

        # try to start EVM
        logger.info('Checking appliance evmserverd service')
        try:
            self.restart_evm_service()
        except ApplianceException as ex:
            return 'evmserverd failed to start:\n{}'.format(ex.args[0])

        # This should be pretty comprehensive, but we might add some net_checks for
        # 3000, 4000, and 80 at this point, and waiting a reasonable amount of time
        # before exploding if any of them don't appear in time after evm restarts.

    def fix_ntp_clock(self, log_callback=None):
        """Fixes appliance time using ntpdate on appliance"""
        if log_callback is None:
            log_callback = self.log.info
        log_callback('Fixing appliance clock')
        client = self.ssh_client()
        try:
            ntp_server = random.choice(conf.cfme_data['clock_servers'])
        except IndexError:
            msg = 'No clock servers configured in cfme_data.yaml'
            log_callback(msg)
            raise Exception(msg)

        status, out = client.run_command("ntpdate {}".format(ntp_server))
        if status != 0:
            self.log.error('ntpdate failed:')
            self.log.error(out)
            msg = 'Setting the time failed on appliance'
            log_callback(msg)
            raise Exception(msg)

    def workaround_missing_gemfile(self, log_callback=None):
        """Fix Gemfile issue.

        Early 5.4 builds have issues with Gemfile not present (BUG 1191496). This circumvents the
        issue with pointing the env variable that Bundler uses to get the Gemfile to the Gemfile in
        vmdb which *should* be correct.

        When this issue is resolved, this method will do nothing.
        """
        if log_callback is None:
            log_callback = self.log.info
        client = self.ssh_client()
        status, out = client.run_command("ls /opt/rh/cfme-gemset")
        if status != 0:
            return  # Not needed
        log_callback('Fixing Gemfile issue')
        # Check if the error is there
        status, out = client.run_rails_command("puts 1")
        if status == 0:
            return  # All OK!
        client.run_command('echo "export BUNDLE_GEMFILE=/var/www/miq/vmdb/Gemfile" >> /etc/bashrc')
        # To be 100% sure
        self.reboot(wait_for_web_ui=False, log_callback=log_callback)

    def precompile_assets(self, log_callback=None):
        """Precompile the static assets (images, css, etc) on an appliance

        Not required on 5.2 appliances

        """
        # compile assets if required (not required on 5.2)
        if self.version.is_in_series("5.2"):
            return
        if log_callback is None:
            log_callback = self.log.info
        log_callback('Precompiling assets')

        client = self.ssh_client()
        status, out = client.run_rake_command("assets:precompile")

        if status != 0:
            msg = 'Appliance {} failed to precompile assets'.format(self.address)
            log_callback(msg)
            raise ApplianceException(msg)
        else:
            self.restart_evm_service()

        return status

    def setup_upstream_db(self, log_callback=None):
        """Configure upstream database

        Note:
            This is a workaround put in place to get upstream appliance provisioning working again

        """
        if self.version != LATEST:
            return

        if log_callback is None:
            log_callback = lambda msg: self.log.info("DB setup: {}".format(msg))
        else:
            cb = log_callback
            log_callback = lambda msg: cb("DB setup: {}".format(msg))

        client = self.ssh_client()

        # Make sure the database is ready
        log_callback('Starting upstream db setup')
        wait_for(func=lambda: self.db_online,
            message='appliance db online', delay=20, num_sec=120)

        if self.db_has_database and self.db_has_tables:
            log_callback('db already configured')
            return

        # Make sure the working dir exists
        result = client.run_rails_command(
            dedent("""\
            "
            require 'trollop'

            # spoof the trollop options method so region is set correctly
            module Trollop
              class << self
                def options(*args)
                  return {:region => 0}
                end
              end
            end

            # now load the rake tasks and invoke
            Rails.application.load_tasks
            Rake.application['evm:db:region'].invoke
            "
        """)
        )

        if result.rc != 0:
            msg = 'DB setup failed'
            log_callback(msg)
            raise ApplianceException(msg)
        else:
            log_callback('DB setup complete')

        self.restart_evm_service(log_callback=log_callback)

        return result

    def clone_domain(self, source="ManageIQ", dest="Default", log_callback=None):
        """Clones Automate domain

        Args:
            src: Source domain name.
            dst: Destination domain name.

        Note:
            Not required (and does not do anything) on 5.2 appliances

        """
        if self.version.is_in_series("5.2"):
            return

        if log_callback is None:
            log_callback = lambda msg: self.log.info("Clone automate domain: {}".format(msg))
        else:
            cb = log_callback
            log_callback = lambda msg: cb("Clone automate domain: {}".format(msg))

        client = self.ssh_client()

        # Make sure the database is ready
        log_callback('Waiting for database')
        self.wait_for_db()

        # Make sure the working dir exists
        client.run_command('mkdir -p /tmp/miq')

        export_opts = 'DOMAIN={} EXPORT_DIR=/tmp/miq PREVIEW=false OVERWRITE=true'.format(source)
        export_cmd = 'evm:automate:export {}'.format(export_opts)
        log_callback('Exporting domain ({}) ...'.format(export_cmd))
        status, output = client.run_rake_command(export_cmd)
        if status != 0:
            msg = 'Failed to export {} domain'.format(source)
            log_callback(msg)
            raise ApplianceException(msg)

        ro_fix_cmd = "sed -i 's/system: true/system: false/g' /tmp/miq/ManageIQ/__domain__.yaml"
        status, output = client.run_command(ro_fix_cmd)
        if status != 0:
            msg = 'Setting {} domain to read/write failed'.format(dest)
            log_callback(msg)
            raise ApplianceException(msg)

        import_opts = 'DOMAIN={} IMPORT_DIR=/tmp/miq PREVIEW=false'.format(source)
        import_opts += ' OVERWRITE=true IMPORT_AS={}'.format(dest)
        import_cmd = 'evm:automate:import {}'.format(import_opts)
        log_callback('Importing domain ({}) ...'.format(import_cmd))
        status, output = client.run_rake_command(import_cmd)
        if status != 0:
            msg = 'Failed to import {} domain'.format(dest)
            log_callback(msg)
            raise ApplianceException(msg)

        return status, output

    def deploy_merkyl(self, start=False, log_callback=None):
        """Deploys the Merkyl log relay service to the appliance"""
        if log_callback is None:
            log_callback = lambda msg: self.log.info("Deploying merkyl: {}".format(msg))
        else:
            cb = log_callback
            log_callback = lambda msg: cb("Deploying merkyl: {}".format(msg))

        client = self.ssh_client()

        client.run_command('mkdir -p /root/merkyl')
        for filename in ['__init__.py', 'merkyl.tpl', ('bottle.py.dontflake', 'bottle.py'),
                         'allowed.files']:
            try:
                src, dest = filename
            except (TypeError, ValueError):
                # object is not iterable or too many values to unpack
                src = dest = filename
            log_callback('Sending {} to appliance'.format(src))
            client.put_file(data_path.join(
                'bundles', 'merkyl', src).strpath, os.path.join('/root/merkyl', dest))

        client.put_file(data_path.join(
            'bundles', 'merkyl', 'merkyl').strpath, os.path.join('/etc/init.d/merkyl'))
        client.run_command('chmod 775 /etc/init.d/merkyl')
        client.run_command(
            '/bin/bash -c \'if ! [[ $(iptables -L -n | grep "state NEW tcp dpt:8192") ]]; then '
            'iptables -I INPUT 6 -m state --state NEW -m tcp -p tcp --dport 8192 -j ACCEPT; fi\'')

        if start:
            log_callback("Starting ...")
            client.run_command('service merkyl restart')
            log_callback("Setting it to start after reboot")
            client.run_command("chkconfig merkyl on")

    def update_rhel(self, *urls, **kwargs):
        """Update RHEL on appliance

        Will pull URLs from the 'updates_urls' environment variable (whitespace-separated URLs),
        or cfme_data.

        If the env var is not set, URLs will be pulled from cfme_data.
        If the env var is set, it is the only source for update URLs.

        Generic rhel update URLs cfme_data['basic_info']['rhel_updates_urls'] (yaml list)
        On downstream builds, an additional RH SCL updates url can be inserted at
        cfme_data['basic_info']['rhscl_updates_urls'].


        """
        urls = list(urls)
        log_callback_f = kwargs.pop("log_callback", lambda msg: self.log.info)
        reboot = kwargs.pop("reboot", True)
        log_callback = lambda msg: log_callback_f("Update RHEL: {}".format(msg))
        log_callback('updating appliance')
        if not urls:
            basic_info = conf.cfme_data.get('basic_info', {})
            if os.environ.get('updates_urls'):
                # try to pull URLs from env if var is non-empty
                urls.extend(os.environ['update_urls'].split())
            else:
                # fall back to cfme_data
                updates_url = basic_info.get('rhel_updates_url')
                if updates_url:
                    urls.append(updates_url)

                if self.version.is_in_series("5.3"):
                    rhscl_url = basic_info.get('rhscl_updates_url')
                    if rhscl_url:
                        urls.append(rhscl_url)

        client = self.ssh_client()

        # create repo file
        log_callback('Creating repo file on appliance')
        write_updates_repo = 'cat > /etc/yum.repos.d/updates.repo <<EOF\n'
        for i, url in enumerate(urls):
            write_updates_repo += dedent('''\
                [update-{i}]
                name=update-url-{i}
                baseurl={url}
                enabled=1
                gpgcheck=0
                ''').format(i=i, url=url)
        write_updates_repo += 'EOF\n'
        status, out = client.run_command(write_updates_repo)
        if status != 0:
            msg = 'Failed to write repo updates repo to appliance'
            log_callback(msg)
            raise Exception(msg)

        # update
        log_callback('Running rhel updates on appliance')
        status, out = client.run_command('yum update -y --nogpgcheck')
        if status != 0:
            self.log.error('appliance update failed')
            self.log.error(out)
            msg = 'Appliance {} failed to update RHEL, error in logs'.format(self.address)
            log_callback(msg)
            raise ApplianceException(msg)

        if reboot:
            self.reboot(wait_for_web_ui=False, log_callback=log_callback)

        return status, out

    def patch_ajax_wait(self, reverse=False, log_callback=None):
        """Patches ajax wait code

        Args:
            reverse: Will reverse the ajax wait code patch if set to ``True``

        Note:
            Does nothing for versions including and above 5.3

        """
        if self.version >= '5.3':
            return

        if log_callback is None:
            log_callback = lambda msg: self.log.info("Patch ajax wait: {}".format(msg))
        else:
            cb = log_callback
            log_callback = lambda msg: cb("Patch ajax wait: {}".format(msg))

        log_callback('Starting')

        # Find the patch file
        patch_file_name = datafile.data_path_for_filename('ajax_wait.diff', scripts_path.strpath)

        # Set up temp dir
        tmpdir = mkdtemp()
        atexit.register(shutil.rmtree, tmpdir)
        source = '/var/www/miq/vmdb/public/javascripts/application.js'
        target = os.path.join(tmpdir, 'application.js')

        client = self.ssh_client()
        log_callback('Retrieving appliance.js from appliance')
        client.get_file(source, target)

        os.chdir(tmpdir)
        # patch, level 4, patch direction (default forward), ignore whitespace, don't output rejects
        direction = '-N -R' if reverse else '-N'
        exitcode = subprocess.call('patch -p4 %s -l -r- < %s' % (direction, patch_file_name),
            shell=True)

        if exitcode == 0:
            # Put it back after successful patching.
            log_callback('Replacing appliance.js on appliance')
            client.put_file(target, source)
        else:
            log_callback('Patch failed, not changing appliance')

        return exitcode

    def loosen_pgssl(self, with_ssl=False, log_callback=None):
        """Loosens postgres connections

        Note:
            Not required (and does not do anything) on 5.2 appliances

        """
        if self.version.is_in_series("5.2"):
            return

        (log_callback or self.log.info)('Loosening postgres permissions')

        # Init SSH client
        client = self.ssh_client()

        # set root password
        cmd = "psql -d vmdb_production -c \"alter user {} with password '{}'\"".format(
            conf.credentials['database']['username'], conf.credentials['database']['password']
        )
        client.run_command(cmd)

        # back up pg_hba.conf
        client.run_command('mv /opt/rh/postgresql92/root/var/lib/pgsql/data/pg_hba.conf '
            '/opt/rh/postgresql92/root/var/lib/pgsql/data/pg_hba.conf.sav')

        if with_ssl:
            ssl = 'hostssl all all all cert map=sslmap'
        else:
            ssl = ''

        # rewrite pg_hba.conf
        write_pg_hba = dedent("""\
        cat > /opt/rh/postgresql92/root/var/lib/pgsql/data/pg_hba.conf <<EOF
        local all postgres,root trust
        host all all 0.0.0.0/0 md5
        {ssl}
        EOF
        """.format(ssl=ssl))
        client.run_command(write_pg_hba)
        client.run_command("chown postgres:postgres "
            "/opt/rh/postgresql92/root/var/lib/pgsql/data/pg_hba.conf")

        # restart postgres
        status, out = client.run_command("service postgresql92-postgresql restart")
        return status

    def browser_session(self):
        """Creates browser session connected to this appliance

        Returns: Browser session connected to this appliance.

        Usage:
            with appliance.browser_session() as browser:
                browser.do_stuff(TM)
        """
        return browser_session(base_url=self.url)

    def enable_internal_db(self, region=0, key_address=None, db_password=None,
                           ssh_password=None, log_callback=None):
        """Enables internal database

        Args:
            region: Region number of the CFME appliance.
            key_address: Address of CFME appliance where key can be fetched.

        Note:
            If key_address is None, a new encryption key is generated for the appliance.
        """
        (log_callback or self.log.info)(
            'Enabling internal DB (region {}) on {}.'.format(region, self.address))
        self.db_address = self.address
        del(self.db)

        client = self.ssh_client()

        # Defaults
        db_password = db_password or conf.credentials['database']['password']
        ssh_password = ssh_password or conf.credentials['ssh']['password']

        if self.has_cli:
            # use the cli
            if key_address:
                status, out = client.run_command(
                    'appliance_console_cli --region {} --internal --fetch-key {} -p {} -a {}'
                    .format(region, key_address, db_password, ssh_password)
                )
            else:
                status, out = client.run_command(
                    'appliance_console_cli --region {} --internal --force-key -p {}'
                    .format(region, db_password)
                )
        else:
            # no cli, use the enable internal db script
            rbt_repl = {
                'miq_lib': '/var/www/miq/lib',
                'region': region
            }

            # Find and load our rb template with replacements
            rbt = datafile.data_path_for_filename('enable-internal-db.rbt', scripts_path.strpath)
            rb = datafile.load_data_file(rbt, rbt_repl)

            # sent rb file over to /tmp
            remote_file = '/tmp/%s' % generate_random_string()
            client.put_file(rb.name, remote_file)

            # Run the rb script, clean it up when done
            status, out = client.run_command('ruby %s' % remote_file)
            client.run_command('rm %s' % remote_file)

        return status, out

    def enable_external_db(self, db_address, region=0, db_name=None,
            db_username=None, db_password=None, log_callback=None):
        """Enables external database

        Args:
            db_address: Address of the external database
            region: Number of region to join
            db_name: Name of the external DB
            db_username: Username to access the external DB
            db_password: Password to access the external DB

        Returns a tuple of (exitstatus, script_output) for reporting, if desired
        """
        if log_callback is None:
            log_callback = self.log.info
        log_callback('Enabling external DB (db_address {}, region {}) on {}.'
            .format(db_address, region, self.address))
        # reset the db address and clear the cached db object if we have one
        self.db_address = db_address
        del(self.db)

        # default
        db_name = db_name or 'vmdb_production'
        db_username = db_username or conf.credentials['database']['username']
        db_password = db_password or conf.credentials['database']['password']

        client = self.ssh_client()

        if self.has_cli:
            # copy v2 key
            master_client = client(hostname=self.db_address)
            rand_filename = "/tmp/v2_key_{}".format(generate_random_string())
            master_client.get_file("/var/www/miq/vmdb/certs/v2_key", rand_filename)
            client.put_file(rand_filename, "/var/www/miq/vmdb/certs/v2_key")

            # enable external DB with cli
            status, out = client.run_command(
                'appliance_console_cli '
                '--hostname {} --region {} --dbname {} --username {} --password {}'.format(
                    self.db_address, region, db_name, db_username, db_password
                )
            )
        else:
            # no cli, use the enable external db script
            rbt_repl = {
                'miq_lib': '/var/www/miq/lib',
                'host': self.db_address,
                'region': region,
                'database': db_name,
                'username': db_username,
                'password': db_password
            }

            # Find and load our rb template with replacements
            rbt = datafile.data_path_for_filename('enable-internal-db.rbt', scripts_path.strpath)
            rb = datafile.load_data_file(rbt, rbt_repl)

            # Init SSH client and sent rb file over to /tmp
            remote_file = '/tmp/%s' % generate_random_string()
            client.put_file(rb.name, remote_file)

            # Run the rb script, clean it up when done
            status, out = client.run_command('ruby %s' % remote_file)
            client.run_command('rm %s' % remote_file)

        if status != 0:
            self.log.error('error enabling external db')
            self.log.error(out)
            msg = ('Appliance {} failed to enable external DB running on {}'
                  .format(self.address, db_address))
            log_callback(msg)
            raise ApplianceException(msg)

        return status, out

    def _check_appliance_ui_wait_fn(self):
        # Get the URL, don't verify ssl cert
        try:
            response = requests.get(self.url, timeout=15, verify=False)
            if response.status_code == 200:
                self.log.info("Appliance online")
                return True
            else:
                self.log.debug('Appliance online, status code %d' % response.status_code)
        except requests.exceptions.Timeout:
            self.log.debug('Appliance offline, connection timed out')
        except ValueError:
            # requests exposes invalid URLs as ValueErrors, which is excellent
            raise
        except Exception as ex:
            self.log.debug('Appliance online, but connection failed: %s' % ex.message)
        return False

    def is_web_ui_running(self, unsure=False):
        """Triple checks if web UI is up and running

        Args:
            unsure: Variable to return when not sure if web UI is running or not
                    (default ``False``)

        """
        num_of_tries = 3
        was_running_count = 0
        for try_num in range(num_of_tries):
            if self._check_appliance_ui_wait_fn():
                was_running_count += 1
            sleep(3)

        if was_running_count == 0:
            return False
        elif was_running_count == num_of_tries:
            return True
        else:
            return unsure

    def restart_evm_service(self, log_callback=None):
        """Restarts the ``evmserverd`` service on this appliance
        """
        if log_callback is None:
            log_callback = self.log.info
        log_callback('restarting evm service')
        with self.ssh_client() as ssh:
            status, msg = ssh.run_command('service evmserverd restart')
            if status != 0:
                msg = 'Failed to restart evmserverd on {}\nError: {}'.format(self.address, msg)
                log_callback(msg)
                raise ApplianceException(msg)

    def reboot(self, wait_for_web_ui=True, log_callback=None):
        (log_callback or self.log.info)('Rebooting appliance')
        client = self.ssh_client()

        old_uptime = client.uptime()
        status, out = client.run_command('reboot')

        wait_for(lambda: client.uptime() < old_uptime, handle_exception=True,
            num_sec=300, message='appliance to reboot', delay=10)

        if wait_for_web_ui:
            self.wait_for_web_ui()

    def wait_for_web_ui(self, timeout=900, running=True, log_callback=None):
        """Waits for the web UI to be running / to not be running

        Args:
            timeout: Number of seconds to wait until timeout (default ``600``)
            running: Specifies if we wait for web UI to start or stop (default ``True``)
                     ``True`` == start, ``False`` == stop
        """
        (log_callback or self.log.info)('Waiting for web UI to appear')
        result, wait = wait_for(self._check_appliance_ui_wait_fn, num_sec=timeout,
            fail_condition=not running, delay=10)
        return result

    def install_vddk(self, reboot=True, force=False, vddk_url=None, log_callback=None):
        '''Install the vddk on a appliance'''
        if log_callback is None:
            log_callback = self.log.info

        def log_raise(exception_class, message):
            log_callback(message)
            raise exception_class(message)

        log_callback('vddk_url: {}'.format(str(vddk_url)))
        if vddk_url is None:
            vddk_url = conf.cfme_data.get("basic_info", {}).get("vddk_url", None)
            log_callback('basic_info: {}'.format(str(conf.cfme_data.get("basic_info", {}))))
            log_callback('vddk_url: {}'.format(str(vddk_url)))
        log_callback('vddk_url: {}'.format(str(vddk_url)))
        if vddk_url is None:
            raise Exception("vddk_url not specified!")

        with self.ssh_client() as client:
            is_already_installed = False
            if client.run_command('test -d /usr/lib/vmware-vix-disklib/lib64')[0] == 0:
                is_already_installed = True

            if not is_already_installed or force:

                # start
                filename = vddk_url.split('/')[-1]

                # download
                log_callback('Downloading VDDK')
                result = client.run_command('curl {} -o {}'.format(vddk_url, filename))
                if result.rc != 0:
                    log_raise(Exception, "Could not download VDDK")

                # extract
                log_callback('Extracting vddk')
                status, out = client.run_command('tar xvf {}'.format(filename))
                if status != 0:
                    log_raise(Exception, "Error: Unknown format of the file:\n{}".format(out))

                # install
                log_callback('Installing vddk')
                status, out = client.run_command(
                    'vmware-vix-disklib-distrib/vmware-install.pl --default EULA_AGREED=yes')
                if status != 0:
                    log_raise(
                        Exception, 'VDDK installation failure (rc: {})\n{}'.format(out, status))
                else:
                    client.run_command('ldconfig')

                # verify
                log_callback('Verifying vddk')
                status, out = client.run_command('ldconfig -p | grep vix')
                if len(out) < 2:
                    log_raise(
                        Exception,
                        "Potential installation issue, libraries not detected\n{}".format(out))

                # 5.2 workaround
                if self.version.is_in_series("5.2"):
                    # find the vixdisk libs and add it to cfme 5.2 lib path which was hard coded for
                    #    vddk v2.1 and v5.1
                    log_callback('WARN: Adding 5.2 workaround')
                    status, out = client.run_command(
                        "find /usr/lib/vmware-vix-disklib/lib64 -maxdepth 1 -type f -exec ls"
                        " -d {} + | grep libvixDiskLib")
                    for file in str(out).split("\n"):
                        client.run_command("cd /var/www/miq/lib/VixDiskLib/vddklib; ln -s " + file)

                # reboot
                if reboot:
                    log_callback('Appliance reboot')
                    old_uptime = client.uptime()
                    status, out = client.run_command('reboot')
                    wait_for(
                        lambda: client.uptime() < old_uptime,
                        handle_exception=True, num_sec=300, message='appliance to reboot', delay=10)
                else:
                    log_callback('A reboot is required before vddk will work')

    def wait_for_db(self, timeout=600):
        """Waits for appliance database to be ready

        Args:
            timeout: Number of seconds to wait until timeout (default ``180``)
        """
        wait_for(func=lambda: self.is_db_ready,
                 message='appliance.is_db_ready',
                 delay=20,
                 num_sec=timeout)

    def wait_for_ssh(self, timeout=300):
        """Waits for appliance database to be ready

        Args:
            timeout: Number of seconds to wait until timeout (default ``180``)
        """
        wait_for(func=lambda: self.is_ssh_running,
                 message='appliance.is_ssh_running',
                 delay=5,
                 num_sec=timeout)

    @lazycache
    def db_address(self):
        # pulls the db address from the appliance by default, falling back to the appliance
        # ip address (and issuing a warning) if that fails. methods that set up the internal
        # db should set db_address to something else when they do that
        result = self.ssh_client().run_rails_command(
            "\"puts Rails.configuration.database_configuration['production']['host']\"")
        # output can be empty, in which case the database is local
        if result.rc == 0:
            stripped_out = result.output.strip()
            if stripped_out.startswith('127') or 'localhost' in stripped_out:
                # address is localhost, use the appliance address
                stripped_out = None
            return stripped_out if stripped_out else self.address
        else:
            self.log.warning('Unable to pull database address from appliance')
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
        # Using 'and' chain instead of all(...) to
        # prevent calling more things after a step fails
        return self.db_online and self.db_has_database and self.db_has_tables

    @property
    def db_online(self):
        db_check_command = ('psql -U postgres -t  -c "select now()" postgres')
        result = self.db_ssh_client().run_command(db_check_command)
        return result.rc == 0

    @property
    def db_has_database(self):
        db_check_command = ('psql -U postgres -t  -c "SELECT datname FROM pg_database '
            'WHERE datname LIKE \'vmdb_%\';" postgres | grep -q vmdb_production')
        result = self.db_ssh_client().run_command(db_check_command)
        return result.rc == 0

    @property
    def db_has_tables(self):
        db_check_command = ('psql -U postgres -t  -c "SELECT * FROM information_schema.tables '
            'WHERE table_schema = \'public\';" vmdb_production | grep -q vmdb_production')
        result = self.db_ssh_client().run_command(db_check_command)
        return result.rc == 0

    @property
    def is_ssh_running(self):
        return net_check(22, self.address, force=True)

    @property
    def has_cli(self):
        if self.ssh_client().run_command('ls -l /bin/appliance_console_cli')[0] == 0:
            return True
        else:
            return False

    @lazycache
    def build_datetime(self):
        datetime = self.ssh_client().get_build_datetime()
        return datetime

    @lazycache
    def is_downstream(self):
        return self.ssh_client().is_appliance_downstream()

    def has_netapp(self):
        return self.ssh_client().appliance_has_netapp()

    @lazycache
    def guid(self):
        result = self.ssh_client().run_command('cat /var/www/miq/vmdb/GUID')
        return result.output

    @lazycache
    def configuration_details(self):
        """Return details that are necessary to navigate through Configuration accordions.

        Args:
            ip_address: IP address of the server to match. If None, uses hostname from
                ``conf.env['base_url']``

        Returns:
            If the data weren't found in the DB, :py:class:`NoneType`
            If the data were found, it returns tuple ``(region, server name,
            server id, server zone id)``
        """
        return db_queries.get_configuration_details(self.db)

    def server_id(self):
        try:
            return self.configuration_details[2]
        except TypeError:
            return None

    def server_region(self):
        try:
            return self.configuration_details[0]
        except TypeError:
            return None

    def server_name(self):
        try:
            return self.configuration_details[1]
        except TypeError:
            return None

    def server_zone_id(self):
        try:
            return self.configuration_details[3]
        except TypeError:
            return None

    @lazycache
    def zone_description(self):
        return db_queries.get_zone_description(self.server_zone_id(), db=self.db)

    @lazycache
    def host_id(self, hostname):
        return db_queries.get_host_id(hostname, db=self.db)

    @lazycache
    def db_yamls(self):
        return db.db_yamls(self.db, self.guid)

    def get_yaml_config(self, config_name):
        return self.db_yamls[config_name]

    def install_coverage(self):
        self._coverage_install_simplecov()
        self._coverage_install_coverage_hook()
        self.restart_evm_service()
        self._coverage_touch_all_the_things()
        self.wait_for_web_ui()

    def collect_coverage_reports(self):
        self._coverage_stop_touching_all_the_things()
        self._coverage_collect_reports()

    @lazycache
    def coverage_results_archive(self):
        return ui_coverage.coverage_output_dir.join(
            '{}-coverage-results.tgz'.format(self.address)
        ).strpath

    def _coverage_install_simplecov(self):
        self.log.info('Installing coverage gems on appliance')
        self.ssh_client().put_file(ui_coverage.gemfile.strpath, ui_coverage.rails_root.strpath)
        x, out = self.ssh_client().run_command('cd {}; bundle'.format(ui_coverage.rails_root))
        return x == 0

    def _coverage_install_coverage_hook(self):
        self.log.info('Installing coverage hook on appliance')
        # Clean appliance coverage dir
        self.ssh_client().run_command('rm -rf {}'.format(
            ui_coverage.appliance_coverage_root.strpath))
        # Put the coverage hook in the miq lib path
        self.ssh_client().put_file(ui_coverage.coverage_hook.strpath, ui_coverage.rails_root.join(
            '..', 'lib', ui_coverage.coverage_hook.basename).strpath)
        replacements = {
            'require': r"require 'coverage_hook'",
            'config': ui_coverage.rails_root.join('config').strpath
        }
        # grep/echo to try to add the require line only once
        # This goes in preinitializer after the miq lib path is set up,
        # which makes it so ruby can actually require the hook
        command_template = (
            'cd {config};'
            'grep -q "{require}" preinitializer.rb || echo -e "\\n{require}" >> preinitializer.rb'
        )
        x, out = self.ssh_client().run_command(command_template.format(**replacements))
        return x == 0

    def _coverage_restart_evm(self, rude=True):
        self.log.info('Restarting EVM to enable coverage reporting')
        # This is rude by default (issuing a kill -9 on ruby procs), since the most common use-case
        # will be to set up coverage on a freshly provisioned appliance in a jenkins run
        if rude:
            x, out = self.ssh_client().run_command('killall -9 ruby; service evmserverd start')
        else:
            x, out = self.ssh_client().run_comment('service evmserverd restart')
        return x == 0

    def _coverage_touch_all_the_things(self):
        self.log.info('Establishing baseline overage by requiring ALL THE THINGS')
        # send over the thing toucher
        self.ssh_client().put_file(
            ui_coverage.thing_toucher.strpath, ui_coverage.rails_root.join(
                ui_coverage.thing_toucher.basename).strpath
        )
        # start it in an async process so we can go one testing while this takes place
        self._thing_toucher_proc = Process(target=ui_coverage._thing_toucher_mp_handler,
            args=[self.ssh_client()])
        self._thing_toucher_proc.start()

    def _coverage_stop_touching_all_the_things(self):
        self.log.info('Waiting for baseline coverage generator to finish')
        # block while the thing toucher is still running
        if self._thing_toucher_proc is not None:
            self._thing_toucher_proc.join()
            return self._thing_toucher_proc.exitcode == 0

    def _coverage_collect_reports(self):
        # restart evm to stop the proccesses and let the simplecov exit hook run
        self.ssh_client().run_command('service evmserverd restart')
        # then copy the remote coverage dir into it
        self.log.info("Collecting coverage reports from {}".format(self.address))
        self.log.info("Report collection can take several minutes")
        # find all the resultsets, strip the leading path element, and tar them up
        # tar structure will be ipaddress/pid/.resultset.json
        # we can make a ton of resultsets, so tarring saves a lot of time
        self.ssh_client().run_command('find /var/www/miq/vmdb/coverage -name ".resultset.json" |'
            'sed "s#/var/www/miq/vmdb/coverage/##" |'
            'tar cvzf /tmp/ui-coverage-results.tgz -C /var/www/miq/vmdb/coverage -T -')
        self.ssh_client().get_file('/tmp/ui-coverage-results.tgz', self.coverage_results_archive)


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
        If no matching template for given version is found, and trackerbot is set up,
        the latest available template of the same stream will be used.
        E.g.: if there is no template for 5.2.5.1 but there is 5.2.5.3, it will be used instead.
        If both template name and version are specified, template name takes priority.

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

    def _get_latest_template():
        api = trackerbot.api()
        stream = get_stream(version)
        template_data = trackerbot.latest_template(api, stream, provider_name)
        return template_data.get('latest_template', None)

    if provider_name is None:
        provider_name = conf.cfme_data['appliance_provisioning']['default_provider']

    if template is not None:
        template_name = template
    elif version is not None:
        templates_by_version = conf.cfme_data['appliance_provisioning'].get('versions', dict())
        try:
            template_name = templates_by_version[version]
        except KeyError:
            # We try to get the latest template from the same stream - if trackerbot is set up
            if conf.env.get('trackerbot', {}):
                template_name = _get_latest_template()
                if not template_name:
                    raise ApplianceException('No template found for stream {} on provider {}'
                        .format(get_stream(version), provider_name))
                logger.warning('No template found matching version {}, using {} instead.'
                               .format(version, template_name))
            else:
                raise ApplianceException('No template found matching version {}'.format(version))
    else:
        raise ApplianceException('Either version or template name must be specified')

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
    except Exception as e:
        logger.exception(e)
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
