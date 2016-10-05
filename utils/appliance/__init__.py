# -*- coding: utf-8 -*-
import fauxfactory
import hashlib
import os
import random
import re
import socket
import yaml
from textwrap import dedent
from time import sleep
from urlparse import ParseResult, urlparse
from tempfile import NamedTemporaryFile

from cached_property import cached_property

from werkzeug.local import LocalStack, LocalProxy

import dateutil.parser
import requests
import traceback

from navmazing import NavigateToSibling
from sentaku import ImplementationContext
from utils.mgmt_system import RHEVMSystem
from mgmtsystem.virtualcenter import VMWareSystem

from fixtures import ui_coverage
from fixtures.pytest_store import store
from utils import api, conf, datafile, db, db_queries, ssh, ports
from utils.datafile import load_data_file
from utils.events import EventTool
from utils.log import logger, create_sublogger, logger_wrap
from utils.appliance.endpoints.ui import navigator, CFMENavigateStep
from utils.net import net_check, resolve_hostname
from utils.path import data_path, patches_path, scripts_path
from utils.version import Version, get_stream, pick, LATEST
from utils.wait import wait_for
from utils import clear_property_cache

from .endpoints.ui import ViaUI

RUNNING_UNDER_SPROUT = os.environ.get("RUNNING_UNDER_SPROUT", "false") != "false"


def _current_miqqe_version():
    """Parses MiqQE JS patch version from the patch file

    Returns: Version as int
    """
    with patches_path.join('miq_application.js.diff').open("r") as f:
        match = re.search("MiqQE_version = (\d+);", f.read(), flags=0)
    version = int(match.group(1))
    return version

current_miqqe_version = _current_miqqe_version()


class ApplianceException(Exception):
    pass


class IPAppliance(object):
    """IPAppliance represents an already provisioned cfme appliance whos provider is unknown
    but who has an IP address. This has a lot of core functionality that Appliance uses, since
    it knows both the provider, vm_name and can there for derive the IP address.

    Args:
        ipaddress: The IP address of the provider
        browser_streal: If True then then current browser is killed and the new appliance
            is used to generate a new session.
    """
    _nav_steps = {}

    def __init__(self, address=None, browser_steal=False, container=None):
        if address is not None:
            if not isinstance(address, ParseResult):
                address = urlparse(str(address))
            if not (address.scheme and address.netloc):
                # Use .path (w.x.y.z ip format)
                self.address = address.path
                self.scheme = "https"
                self._url = "https://{}/".format(address.path)
            else:
                # schema://w.x.y.z/ format
                self.address = address.netloc
                self.scheme = address.scheme
                self._url = address.geturl()
        self.browser_steal = browser_steal
        self.container = container
        self._db_ssh_client = None

        self.browser = ViaUI(owner=self)
        self.sentaku_ctx = ImplementationContext.from_instances(
            [self.browser])

    def __repr__(self):
        return '{}({})'.format(type(self).__name__, repr(self.address))

    def __call__(self, **kwargs):
        """Syntactic sugar for overriding certain instance variables for context managers.

        Currently possible variables are:

        * `browser_steal`
        """
        self.browser_steal = kwargs.get("browser_steal", self.browser_steal)
        return self

    def __enter__(self):
        """ This method will replace the current appliance in the store """
        stack.push(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Fake soft assert to capture the screenshot during the test."""
        from fixtures import artifactor_plugin
        if (
                exc_type is not None and not RUNNING_UNDER_SPROUT):
            from cfme.fixtures.pytest_selenium import take_screenshot
            logger.info("Before we pop this appliance, a screenshot and a traceback will be taken.")
            ss, ss_error = take_screenshot()
            full_tb = "".join(traceback.format_tb(exc_tb))
            short_tb = "{}: {}".format(exc_type.__name__, str(exc_val))
            full_tb = "{}\n{}".format(full_tb, short_tb)

            g_id = "appliance-cm-screenshot-{}".format(fauxfactory.gen_alpha(length=6))

            artifactor_plugin.art_client.fire_hook('filedump',
                slaveid=artifactor_plugin.SLAVEID,
                description="Appliance CM error traceback", contents=full_tb, file_type="traceback",
                display_type="danger", display_glyph="align-justify", group_id=g_id)

            if ss:
                artifactor_plugin.art_client.fire_hook('filedump',
                    slaveid=artifactor_plugin.SLAVEID, description="Appliance CM error screenshot",
                    file_type="screenshot", mode="wb", contents_base64=True, contents=ss,
                    display_glyph="camera", group_id=g_id)
            if ss_error:
                artifactor_plugin.art_client.fire_hook('filedump',
                    slaveid=artifactor_plugin.SLAVEID,
                    description="Appliance CM error screenshot failure", mode="w",
                    contents_base64=False, contents=ss_error, display_type="danger", group_id=g_id)
        elif exc_type is not None:
            logger.info("Error happened but we are not inside a test run so no screenshot now.")
        assert stack.pop() is self, 'appliance stack inconsistent'

    def __eq__(self, other):
        return isinstance(other, IPAppliance) and self.address == other.address

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return int(hashlib.md5(self.address).hexdigest(), 16)

    # Configuration methods
    @logger_wrap("Configure IPAppliance: {}")
    def configure(self, log_callback=None, **kwargs):
        """Configures appliance - database setup, rename, ntp sync

        Utility method to make things easier.

        Args:
            db_address: Address of external database if set, internal database if ``None``
                        (default ``None``)
            name_to_set: Name to set the appliance name to if not ``None`` (default ``None``)
            region: Number to assign to region (default ``0``)
            fix_ntp_clock: Fixes appliance time if ``True`` (default ``True``)
            loosen_pgssl: Loosens postgres connections if ``True`` (default ``True``)
            key_address: Fetch encryption key from this address if set, generate a new key if
                         ``None`` (default ``None``)

        """

        log_callback("Configuring appliance {}".format(self.address))
        with self as ipapp:
            ipapp.wait_for_ssh()
            configure_function = pick({
                '5.2': self._configure_5_2,
                '5.3': self._configure_5_3,
                LATEST: self._configure_upstream,
            })
            configure_function(log_callback=log_callback)

    # When calling any of these methods, `with self:` context must be entered.
    def _configure_5_2(self, log_callback=None):
        self.deploy_merkyl(start=True, log_callback=log_callback)
        self.fix_ntp_clock(log_callback=log_callback)
        self.enable_internal_db(log_callback=log_callback)
        # need to skip_broken here until/unless we see a newer 52z build
        self.update_rhel(log_callback=log_callback, skip_broken=True)
        self.wait_for_web_ui(timeout=1800, log_callback=log_callback)

    def _configure_5_3(self, log_callback=None):
        self.deploy_merkyl(start=True, log_callback=log_callback)
        self.fix_ntp_clock(log_callback=log_callback)
        self.enable_internal_db(log_callback=log_callback)
        self.wait_for_web_ui(timeout=1800, log_callback=log_callback)
        self.loosen_pgssl(log_callback=log_callback)
        # self.ipapp.update_rhel(log_callback=log_callback)
        self.wait_for_web_ui(timeout=1800, log_callback=log_callback)

    def _configure_upstream(self, log_callback=None):
        self.wait_for_evm_service(timeout=1200, log_callback=log_callback)
        self.deploy_merkyl(start=True, log_callback=log_callback)
        self.fix_ntp_clock(log_callback=log_callback)
        self.setup_upstream_db(log_callback=log_callback)
        self.loosen_pgssl(log_callback=log_callback)
        self.restart_evm_service(log_callback=log_callback)
        self.wait_for_web_ui(timeout=1800, log_callback=log_callback)

    def seal_for_templatizing(self):
        """Prepares the VM to be "generalized" for saving as a template."""
        with self.ssh_client as ssh_client:
            # Seals the VM in order to work when spawned again.
            ssh_client.run_command("rm -rf /etc/ssh/ssh_host_*", ensure_host=True)
            if ssh_client.run_command(
                    "grep '^HOSTNAME' /etc/sysconfig/network", ensure_host=True).rc == 0:
                # Replace it
                ssh_client.run_command(
                    "sed -i -r -e 's/^HOSTNAME=.*$/HOSTNAME=localhost.localdomain/' "
                    "/etc/sysconfig/network", ensure_host=True)
            else:
                # Set it
                ssh_client.run_command(
                    "echo HOSTNAME=localhost.localdomain >> /etc/sysconfig/network",
                    ensure_host=True)
            ssh_client.run_command(
                "sed -i -r -e '/^HWADDR/d' /etc/sysconfig/network-scripts/ifcfg-eth0",
                ensure_host=True)
            ssh_client.run_command(
                "sed -i -r -e '/^UUID/d' /etc/sysconfig/network-scripts/ifcfg-eth0",
                ensure_host=True)
            ssh_client.run_command("rm -f /etc/udev/rules.d/70-*", ensure_host=True)
            # Fix SELinux things
            ssh_client.run_command("restorecon -R /etc/sysconfig/network-scripts", ensure_host=True)
            ssh_client.run_command("restorecon /etc/sysconfig/network", ensure_host=True)
            # Stop the evmserverd and move the logs somewhere
            ssh_client.run_command("service evmserverd stop", ensure_host=True)
            ssh_client.run_command("mkdir -p /var/www/miq/vmdb/log/preconfigure-logs",
                ensure_host=True)
            ssh_client.run_command(
                "mv /var/www/miq/vmdb/log/*.log /var/www/miq/vmdb/log/preconfigure-logs/",
                ensure_host=True)
            ssh_client.run_command(
                "mv /var/www/miq/vmdb/log/*.gz /var/www/miq/vmdb/log/preconfigure-logs/",
                ensure_host=True)
            # Reduce swapping, because it can do nasty things to our providers
            ssh_client.run_command('echo "vm.swappiness = 1" >> /etc/sysctl.conf',
                ensure_host=True)

    @property
    def managed_providers(self):
        """Returns a set of providers that are managed by this appliance

        Returns:
            :py:class:`set` of :py:class:`str` - provider_key-s
        """
        ip_addresses = set([])

        # Fetch all providers at once, return empty list otherwise
        try:
            query_res = list(self._query_endpoints())
        except Exception as ex:
            self.log.warning("Unable to query DB for managed providers: %s", str(ex))
            return []

        for ipaddress, hostname in query_res:
            if ipaddress is not None:
                ip_addresses.add(ipaddress)
            elif hostname is not None:
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", hostname) is not None:
                    ip_addresses.add(hostname)
                else:
                    ip_address = resolve_hostname(hostname)
                    if ip_address is not None:
                        ip_addresses.add(ip_address)
        provider_keys = set([])
        for provider_key, provider_data in conf.cfme_data.get("management_systems", {}).iteritems():
            if provider_data.get("ipaddress", None) in ip_addresses:
                provider_keys.add(provider_key)
        return provider_keys

    def _query_endpoints(self):

        if "endpoints" in self.db:
            return self._query_post_endpoints()
        else:
            return self._query_pre_endpoints()

    def _query_pre_endpoints(self):
        ems_table = self.db["ext_management_systems"]
        for ems in self.db.session.query(ems_table):
            yield ems.ipaddress, ems.hostname

    def _query_post_endpoints(self):
        """After Oct 5th, 2015, the ipaddresses and stuff was separated in a separate table."""
        ems_table = self.db["ext_management_systems"]
        ep = self.db["endpoints"]
        for ems in self.db.session.query(ems_table):
            for endpoint in self.db.session.query(ep).filter(ep.resource_id == ems.id):
                ipaddress = endpoint.ipaddress
                hostname = endpoint.hostname
                yield ipaddress, hostname

    @property
    def has_os_infra(self):
        """If there is an OS Infra set up as a provider, some of the UI changes"""
        ems_table = self.db["ext_management_systems"]
        self.db.session.query(ems_table)
        count = self.db.session.query(ems_table).filter(
            ems_table.type == "EmsOpenstackInfra").count()
        return count > 0

    @property
    def has_non_os_infra(self):
        """If there is any non-OS-infra set up as a provider, some of the UI changes"""
        ems_table = self.db["ext_management_systems"]
        self.db.session.query(ems_table)
        count = self.db.session.query(ems_table).filter(
            ems_table.type != "EmsOpenstackInfra").count()
        return count > 0

    @classmethod
    def from_url(cls, url):
        return cls(urlparse(url))

    @cached_property
    def rest_api(self):
        return api.API(
            "{}://{}:{}/api".format(self.scheme, self.address, self.ui_port),
            auth=("admin", "smartvm"))

    @cached_property
    def miqqe_version(self):
        """Returns version of applied JS patch or None if not present"""
        rc, out = self.ssh_client.run_command('grep "[0-9]\+" /var/www/miq/vmdb/.miqqe_version')
        if rc == 0:
            return int(out)
        return None

    @cached_property
    def address(self):
        # If address wasn't set in __init__, use the hostname from base_url
        if getattr(self, "_url", None) is not None:
            parsed_url = urlparse(self._url)
            return parsed_url.netloc
        else:
            parsed_url = urlparse(store.base_url)
            return parsed_url.netloc

    @cached_property
    def hostname(self):
        parsed_url = urlparse(self.url)
        return parsed_url.hostname

    @property
    def ui_port(self):
        parsed_url = urlparse(self.url)
        if parsed_url.port is not None:
            return parsed_url.port
        elif parsed_url.scheme == "https":
            return 443
        elif parsed_url.scheme == "http":
            return 80
        else:
            raise Exception("Unknown scheme {} for {}".format(parsed_url.scheme, store.base_url))

    @cached_property
    def scheme(self):
        return "https"  # By default

    @cached_property
    def url(self):
        return "{}://{}/".format(self.scheme, self.address)

    @cached_property
    def version(self):
        res = self.ssh_client.run_command('cat /var/www/miq/vmdb/VERSION')
        if res.rc != 0:
            raise RuntimeError('Unable to retrieve appliance VMDB version')
        return Version(res.output)

    @cached_property
    def build(self):
        if self.ssh_client.is_appliance_downstream():
            res = self.ssh_client.run_command('cat /var/www/miq/vmdb/BUILD')
            if res.rc != 0:
                raise RuntimeError('Unable to retrieve appliance VMDB version')
            return res.output.strip("\n")
        else:
            return "master"

    @cached_property
    def os_version(self):
        # Currently parses the os version out of redhat release file to allow for
        # rhel and centos appliances
        res = self.ssh_client.run_command(
            r"cat /etc/redhat-release | sed 's/.* release \(.*\) (.*/\1/' #)")
        if res.rc != 0:
            raise RuntimeError('Unable to retrieve appliance OS version')
        return Version(res.output)

    @cached_property
    def log(self):
        return create_sublogger(self.address)

    @cached_property
    def coverage(self):
        return ui_coverage.CoverageManager(self)

    @cached_property
    def ssh_client(self):
        """Creates an ssh client connected to this appliance

        Returns: A configured :py:class:``utils.ssh.SSHClient`` instance.

        Usage:

            with appliance.ssh_client as ssh:
                status, output = ssh.run_command('...')

        Note:

            The credentials default to those found under ``ssh`` key in ``credentials.yaml``.

        """
        if not self.is_ssh_running:
            raise Exception('SSH is unavailable')

        # IPAppliance.ssh_client only connects to its address
        connect_kwargs = {
            'hostname': self.hostname,
            'username': conf.credentials['ssh']['username'],
            'password': conf.credentials['ssh']['password'],
            'container': self.container,
        }
        ssh_client = ssh.SSHClient(**connect_kwargs)
        # FIXME: propperly store ssh clients we made
        store.ssh_clients_to_close.append(ssh_client)
        return ssh_client

    @property
    def db_ssh_client(self, **connect_kwargs):
        # Not lazycached to allow for the db address changing
        if self.is_db_internal:
            return self.ssh_client
        else:
            if self._db_ssh_client is None:
                self._db_ssh_client = self.ssh_client(hostname=self.db_address)
            return self._db_ssh_client

    @property
    def swap(self):
        """Retrieves the value of swap for the appliance. Might raise an exception if SSH fails.

        Return:
            An integer value of swap in the VM in megabytes. If ``None`` is returned, it means it
            was not possible to parse the command output.

        Raises:
            :py:class:`paramiko.ssh_exception.SSHException` or :py:class:`socket.error`
        """
        value = self.ssh_client.run_command(
            'free -m | tr -s " " " " | cut -f 3 -d " " | tail -n 1', reraise=True, timeout=15)
        try:
            value = int(value.output.strip())
        except (TypeError, ValueError):
            value = None
        return value

    @cached_property
    def events(self):
        """Returns an instance of the event capturing class pointed to this appliance."""
        return EventTool(self)

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
            cmd = 'service {}-postgresql restart'.format(db.scl_name())
            result = self.db_ssh_client.run_command(cmd)
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

    @logger_wrap("Fix NTP Clock: {}")
    def fix_ntp_clock(self, log_callback=None):
        """Fixes appliance time using ntpdate on appliance"""
        log_callback('Fixing appliance clock')
        client = self.ssh_client
        try:
            ntp_server = random.choice(conf.cfme_data.get('clock_servers', {}))
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

    @logger_wrap("Patch appliance with MiqQE js: {}")
    def patch_with_miqqe(self, log_callback=None):
        if self.version < "5.5.5.0" or self.version > "5.7.0.3":
            return

        # (local_path, remote_path, md5/None) trio
        autofocus_patch = pick({
            '5.5': 'autofocus.js.diff',
            '5.7': 'autofocus_57.js.diff'
        })
        patch_args = (
            (str(patches_path.join('miq_application.js.diff')),
             '/var/www/miq/vmdb/app/assets/javascripts/miq_application.js',
             None),
            (str(patches_path.join(autofocus_patch)),
             '/var/www/miq/vmdb/app/assets/javascripts/directives/autofocus.js',
             None),
        )

        for local_path, remote_path, md5 in patch_args:
            self.ssh_client.patch_file(local_path, remote_path, md5)

        self.precompile_assets()
        self.restart_evm_service()
        logger.info("Waiting for Web UI to start")
        wait_for(
            func=self.is_web_ui_running,
            message='appliance.is_web_ui_running',
            delay=20,
            timeout=300)
        logger.info("Web UI is up and running")
        self.ssh_client.run_command(
            "echo '{}' > /var/www/miq/vmdb/.miqqe_version".format(current_miqqe_version))
        # Invalidate cached version
        del self.miqqe_version

    @logger_wrap("Work around missing Gem file: {}")
    def workaround_missing_gemfile(self, log_callback=None):
        """Fix Gemfile issue.

        Early 5.4 builds have issues with Gemfile not present (BUG 1191496). This circumvents the
        issue with pointing the env variable that Bundler uses to get the Gemfile to the Gemfile in
        vmdb which *should* be correct.

        When this issue is resolved, this method will do nothing.
        """
        client = self.ssh_client
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

    @logger_wrap("Precompile assets: {}")
    def precompile_assets(self, log_callback=None):
        """Precompile the static assets (images, css, etc) on an appliance

        """
        log_callback('Precompiling assets')
        client = self.ssh_client

        store.terminalreporter.write_line('Precompiling assets')
        store.terminalreporter.write_line(
            'THIS IS NOT STUCK. Just wait until it\'s done, it will be only done once', red=True)
        store.terminalreporter.write_line('Phase 1 of 2: rake assets:clobber')
        status, out = client.run_rake_command("assets:clobber")
        if status != 0:
            msg = 'Appliance {} failed to nuke old assets'.format(self.address)
            log_callback(msg)
            raise ApplianceException(msg)

        store.terminalreporter.write_line('Phase 2 of 2: rake assets:precompile')
        status, out = client.run_rake_command("assets:precompile")
        if status != 0:
            msg = 'Appliance {} failed to precompile assets'.format(self.address)
            log_callback(msg)
            raise ApplianceException(msg)

        store.terminalreporter.write_line('Asset precompilation done')
        return status

    @logger_wrap("Backup database: {}")
    def backup_database(self, log_callback=None):
        """Backup VMDB database

        """
        log_callback('Backing up database')

        with self.ssh_client as ssh:
            status, output = ssh.run_rake_command(
                'evm:db:backup:local -- --local-file /tmp/evm_db.backup --dbname vmdb_production')
            if status != 0:
                msg = 'Failed to backup database'
                log_callback(msg)
                raise ApplianceException(msg)

    @logger_wrap("Restore database: {}")
    def restore_database(self, log_callback=None):
        """Restore VMDB database

        """
        log_callback('Restoring database')

        self.stop_evm_service()

        with self.ssh_client as ssh:
            status, output = ssh.run_rake_command(
                'evm:db:restore:local -- --local-file /tmp/evm_db.backup')
            if status != 0:
                msg = 'Failed to restore database on appl {},output is {}'.format(self.address,
                    output)
                log_callback(msg)
                raise ApplianceException(msg)
            else:
                self.start_evm_service()

    @logger_wrap("Setup upstream DB: {}")
    def setup_upstream_db(self, log_callback=None):
        """Configure upstream database

        Note:
            This is a workaround put in place to get upstream appliance provisioning working again

        """
        if self.version != LATEST:
            return

        log_callback('Starting upstream db setup')

        # Make sure the database is ready
        wait_for(func=lambda: self.is_db_ready,
            message='appliance db ready', delay=20, num_sec=1200)

        log_callback('DB setup complete')

    @logger_wrap("Clone automate domain: {}")
    def clone_domain(self, source="ManageIQ", dest="Default", log_callback=None):
        """Clones Automate domain

        Args:
            src: Source domain name.
            dst: Destination domain name.

        """
        client = self.ssh_client

        # Make sure the database is ready
        log_callback('Waiting for database')
        self.wait_for_db()

        # Make sure the working dir exists
        client.run_command('mkdir -p /tmp/{}'.format(source))

        export_opts = 'DOMAIN={} EXPORT_DIR=/tmp/{} PREVIEW=false OVERWRITE=true'.format(source,
            source)
        export_cmd = 'evm:automate:export {}'.format(export_opts)
        log_callback('Exporting domain ({}) ...'.format(export_cmd))
        status, output = client.run_rake_command(export_cmd)
        if status != 0:
            msg = 'Failed to export {} domain'.format(source)
            log_callback(msg)
            raise ApplianceException(msg)

        ro_fix_cmd = ("sed -i 's/system: true/system: false/g' "
                      "/tmp/{}/{}/__domain__.yaml".format(source, source))
        status, output = client.run_command(ro_fix_cmd)
        if status != 0:
            msg = 'Setting {} domain to read/write failed'.format(dest)
            log_callback(msg)
            raise ApplianceException(msg)

        import_opts = 'DOMAIN={} IMPORT_DIR=/tmp/{} PREVIEW=false'.format(source, source)
        import_opts += ' OVERWRITE=true IMPORT_AS={} ENABLED=true'.format(dest)
        import_cmd = 'evm:automate:import {}'.format(import_opts)
        log_callback('Importing domain ({}) ...'.format(import_cmd))
        status, output = client.run_rake_command(import_cmd)
        if status != 0:
            msg = 'Failed to import {} domain'.format(dest)
            log_callback(msg)
            raise ApplianceException(msg)

        return status, output

    @logger_wrap("Deploying Merkyl: {}")
    def deploy_merkyl(self, start=False, log_callback=None):
        """Deploys the Merkyl log relay service to the appliance"""

        client = self.ssh_client

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

    def get_repofile_list(self):
        """Returns list of repofiles present at the appliance.

        Ignores certain files, like redhat.repo.
        """
        repofiles = self.ssh_client.run_command('ls /etc/yum.repos.d').output.strip().split('\n')
        return [f for f in repofiles if f not in {"redhat.repo"} and f.endswith(".repo")]

    def read_repos(self):
        """Reads repofiles so it gives you mapping of id and url."""
        result = {}
        name_regexp = re.compile(r"^\[update-([^\]]+)\]")
        baseurl_regexp = re.compile(r"baseurl\s*=\s*([^\s]+)")
        for repofile in self.get_repofile_list():
            rc, out = self.ssh_client.run_command("cat /etc/yum.repos.d/{}".format(repofile))
            if rc != 0:
                # Something happened meanwhile?
                continue
            out = out.strip()
            name_match = name_regexp.search(out)
            if name_match is None:
                continue
            baseurl_match = baseurl_regexp.search(out)
            if baseurl_match is None:
                continue
            result[name_match.groups()[0]] = baseurl_match.groups()[0]
        return result

    # Regexp that looks for product type and version in the update URL
    product_url_regexp = re.compile(
        r"/((?:[A-Z]+|CloudForms|rhel|RHEL_Guest))(?:-|/|/server/)(\d+[^/]*)/")

    def find_product_repos(self):
        """Returns a dictionary of products, where the keys are names of product (repos) and values
            are dictionaries where keys are the versions and values the names of the repositories.
        """
        products = {}
        for repo_name, repo_url in self.read_repos().iteritems():
            match = self.product_url_regexp.search(repo_url)
            if match is None:
                continue
            product, ver = match.groups()
            if product not in products:
                products[product] = {}
            products[product][ver] = repo_name
        return products

    def write_repofile(self, repo_id, repo_url, **kwargs):
        """Wrapper around writing a repofile. You can specify conf options in kwargs."""
        if "gpgcheck" not in kwargs:
            kwargs["gpgcheck"] = 0
        if "enabled" not in kwargs:
            kwargs["enabled"] = 1
        filename = "/etc/yum.repos.d/{}.repo".format(repo_id)
        logger.info("Writing a new repofile %s %s", repo_id, repo_url)
        self.ssh_client.run_command('echo "[update-{}]" > {}'.format(repo_id, filename))
        self.ssh_client.run_command('echo "name=update-url-{}" >> {}'.format(repo_id, filename))
        self.ssh_client.run_command('echo "baseurl={}" >> {}'.format(repo_url, filename))
        for k, v in kwargs.iteritems():
            self.ssh_client.run_command('echo "{}={}" >> {}'.format(k, v, filename))
        return repo_id

    def add_product_repo(self, repo_url, **kwargs):
        """This method ensures that when we add a new repo URL, there will be no other version
            of such product present in the yum.repos.d. You can specify conf options in kwargs. They
            will be applied only to newly created repo file.

        Returns:
            The repo id.
        """
        match = self.product_url_regexp.search(repo_url)
        if match is None:
            raise ValueError(
                "The URL {} does not contain information about product and version.".format(
                    repo_url))
        for repo_id, url in self.read_repos().iteritems():
            if url == repo_url:
                # It is already there, so just enable it
                self.enable_disable_repo(repo_id, True)
                return repo_id
        product, ver = match.groups()
        repos = self.find_product_repos()
        if product in repos:
            for v, i in repos[product].iteritems():
                logger.info("Deleting %s repo with version %s (%s)", product, v, i)
                self.ssh_client.run_command("rm -f /etc/yum.repos.d/{}.repo".format(i))
        return self.write_repofile(fauxfactory.gen_alpha(), repo_url, **kwargs)

    def enable_disable_repo(self, repo_id, enable):
        logger.info("%s repository %s", "Enabling" if enable else "Disabling", repo_id)
        return self.ssh_client.run_command(
            "sed -i 's/^enabled=./enabled={}/' /etc/yum.repos.d/{}.repo".format(
                1 if enable else 0, repo_id)).rc == 0

    @logger_wrap("Update RHEL: {}")
    def update_rhel(self, *urls, **kwargs):
        """Update RHEL on appliance

        Will pull URLs from the 'updates_urls' environment variable (whitespace-separated URLs),
        or cfme_data.

        If the env var is not set, URLs will be pulled from cfme_data.
        If the env var is set, it is the only source for update URLs.

        Generic rhel update URLs cfme_data.get('basic_info', {})['rhel_updates_urls'] (yaml list)
        On downstream builds, an additional RH SCL updates url can be inserted at
        cfme_data.get('basic_info', {})['rhscl_updates_urls'].

        If the ``skip_broken`` kwarg is passed, and evaluated as True, broken packages will be
        ignored in the yum update.


        """
        urls = list(urls)
        log_callback = kwargs.pop("log_callback")
        skip_broken = kwargs.pop("skip_broken", False)
        reboot = kwargs.pop("reboot", True)
        streaming = kwargs.pop("streaming", False)
        cleanup = kwargs.pop('cleanup', False)
        log_callback('updating appliance')
        if not urls:
            basic_info = conf.cfme_data.get('basic_info', {})
            if os.environ.get('updates_urls'):
                # try to pull URLs from env if var is non-empty
                urls.extend(os.environ['update_urls'].split())
            else:
                # fall back to cfme_data
                if self.version >= "5.5":
                    updates_url = basic_info.get('rhel7_updates_url')
                else:
                    updates_url = basic_info.get('rhel_updates_url')

                if updates_url:
                    urls.append(updates_url)

        if streaming:
            client = self.ssh_client(stream_output=True)
        else:
            client = self.ssh_client

        if cleanup:
            client.run_command(
                "cd /etc/yum.repos.d && find . -not -name 'redhat.repo' "
                "-not -name 'rhel-source.repo' -not -name . -exec rm {} \;")

        for url in urls:
            self.add_product_repo(url)

        # update
        log_callback('Running rhel updates on appliance')
        # clean yum beforehand to clear metadata from earlier update repos, if any
        try:
            skip = '--skip-broken' if skip_broken else ''
            result = client.run_command('yum update -y --nogpgcheck {}'.format(skip),
                timeout=3600)
        except socket.timeout:
            msg = 'SSH timed out while updating appliance, exiting'
            log_callback(msg)
            # failure to update is fatal, kill this process
            raise KeyboardInterrupt(msg)

        self.log.error(result.output)
        if result.rc != 0:
            self.log.error('appliance update failed')
            msg = 'Appliance {} failed to update RHEL, error in logs'.format(self.address)
            log_callback(msg)
            raise ApplianceException(msg)

        if reboot:
            self.reboot(wait_for_web_ui=False, log_callback=log_callback)

        return result

    def utc_time(self):
        client = self.ssh_client
        status, output = client.run_command('date --iso-8601=seconds -u')
        if not status:
            return dateutil.parser.parse(output)
        else:
            raise Exception("Couldn't get datetime: {}".format(output))

    @logger_wrap("Loosen pgssl: {}")
    def loosen_pgssl(self, with_ssl=False, log_callback=None):
        """Loosens postgres connections"""

        log_callback('Loosening postgres permissions')

        # Init SSH client
        client = self.ssh_client

        # set root password
        cmd = "psql -d vmdb_production -c \"alter user {} with password '{}'\"".format(
            conf.credentials['database']['username'], conf.credentials['database']['password']
        )
        client.run_command(cmd)

        # back up pg_hba.conf
        scl = db.scl_name()
        client.run_command('mv /opt/rh/{scl}/root/var/lib/pgsql/data/pg_hba.conf '
                           '/opt/rh/{scl}/root/var/lib/pgsql/data/pg_hba.conf.sav'.format(scl=scl))

        if with_ssl:
            ssl = 'hostssl all all all cert map=sslmap'
        else:
            ssl = ''

        # rewrite pg_hba.conf
        write_pg_hba = dedent("""\
        cat > /opt/rh/{scl}/root/var/lib/pgsql/data/pg_hba.conf <<EOF
        local all postgres,root trust
        host all all 0.0.0.0/0 md5
        {ssl}
        EOF
        """.format(ssl=ssl, scl=scl))
        client.run_command(write_pg_hba)
        client.run_command("chown postgres:postgres "
            "/opt/rh/{scl}/root/var/lib/pgsql/data/pg_hba.conf".format(scl=scl))

        # restart postgres
        status, out = client.run_command("service {scl}-postgresql restart".format(scl=scl))
        return status

    @logger_wrap("Enable internal DB: {}")
    def enable_internal_db(self, region=0, key_address=None, db_password=None,
                           ssh_password=None, log_callback=None):
        """Enables internal database

        Args:
            region: Region number of the CFME appliance.
            key_address: Address of CFME appliance where key can be fetched.

        Note:
            If key_address is None, a new encryption key is generated for the appliance.
        """
        log_callback('Enabling internal DB (region {}) on {}.'.format(region, self.address))
        self.db_address = self.address
        clear_property_cache(self, 'db')

        client = self.ssh_client

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
                'region': region,
                'scl_name': db.scl_name()
            }

            # Find and load our rb template with replacements
            rbt = datafile.data_path_for_filename('enable-internal-db.rbt', scripts_path.strpath)
            rb = datafile.load_data_file(rbt, rbt_repl)

            # sent rb file over to /tmp
            remote_file = '/tmp/{}'.format(fauxfactory.gen_alphanumeric())
            client.put_file(rb.name, remote_file)

            # Run the rb script, clean it up when done
            status, out = client.run_command('ruby {}'.format(remote_file))
            client.run_command('rm {}'.format(remote_file))

        return status, out

    @logger_wrap("Enable external DB: {}")
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
        log_callback('Enabling external DB (db_address {}, region {}) on {}.'
            .format(db_address, region, self.address))
        # reset the db address and clear the cached db object if we have one
        self.db_address = db_address
        clear_property_cache(self, 'db')

        # default
        db_name = db_name or 'vmdb_production'
        db_username = db_username or conf.credentials['database']['username']
        db_password = db_password or conf.credentials['database']['password']

        client = self.ssh_client

        if self.has_cli:
            # copy v2 key
            master_client = client(hostname=self.db_address)
            rand_filename = "/tmp/v2_key_{}".format(fauxfactory.gen_alphanumeric())
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
            remote_file = '/tmp/{}'.format(fauxfactory.gen_alphanumeric())
            client.put_file(rb.name, remote_file)

            # Run the rb script, clean it up when done
            status, out = client.run_command('ruby {}'.format(remote_file))
            client.run_command('rm {}'.format(remote_file))

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
                self.log.debug('Appliance online, status code %s', response.status_code)
        except requests.exceptions.Timeout:
            self.log.debug('Appliance offline, connection timed out')
        except ValueError:
            # requests exposes invalid URLs as ValueErrors, which is excellent
            raise
        except Exception as ex:
            self.log.debug('Appliance online, but connection failed: %s', str(ex))
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

    def is_evm_service_running(self):
        """checks the ``evmserverd`` service status on this appliance
        """
        with self.ssh_client as ssh:
            status, output = ssh.run_command('service evmserverd status')

            if status == 0:
                msg = 'evmserverd is active(running)'.format(self.address, output)
                self.log.info(msg)
                return True
            return False

    @logger_wrap("Restart EVM Service: {}")
    def restart_evm_service(self, rude=False, log_callback=None):
        """Restarts the ``evmserverd`` service on this appliance
        """
        log_callback('restarting evm service')
        store.terminalreporter.write_line('evmserverd is being restarted, be patient please')
        with self.ssh_client as ssh:
            if rude:
                status, msg = ssh.run_command(
                    'killall -9 ruby;'
                    'service rh-postgresql94-postgresql stop;'
                    'service evmserverd start')
            else:
                status, msg = ssh.run_command('systemctl restart evmserverd')

            if status != 0:
                msg = 'Failed to restart evmserverd on {}\nError: {}'.format(self.address, msg)
                log_callback(msg)
                raise ApplianceException(msg)
        self.server_details_changed()

    @logger_wrap("Stop EVM Service: {}")
    def stop_evm_service(self, log_callback=None):
        """Stops the ``evmserverd`` service on this appliance
        """
        log_callback('stopping evm service')

        with self.ssh_client as ssh:
            status, output = ssh.run_command('service evmserverd stop')

            if status != 0:
                msg = 'Failed to stop evmserverd on {}\nError: {}'.format(self.address, output)
                log_callback(msg)
                raise ApplianceException(msg)

    @logger_wrap("Start EVM Service: {}")
    def start_evm_service(self, log_callback=None):
        """Starts the ``evmserverd`` service on this appliance
        """
        log_callback('starting evm service')

        with self.ssh_client as ssh:
            status, output = ssh.run_command('service evmserverd start')

            if status != 0:
                msg = 'Failed to start evmserverd on {}\nError: {}'.format(self.address, output)
                log_callback(msg)
                raise ApplianceException(msg)

    @logger_wrap("Waiting for evmserverd: {}")
    def wait_for_evm_service(self, timeout=900, log_callback=None):
        """Waits for the evemserverd service to be running

        Args:
            timeout: Number of seconds to wait until timeout (default ``600``)
        """
        (log_callback or self.log.info)('Waiting for evmserverd to be active')
        result, wait = wait_for(self.is_evm_service_running, num_sec=timeout,
                                fail_condition=False, delay=10)
        return result

    @logger_wrap("Rebooting Appliance: {}")
    def reboot(self, wait_for_web_ui=True, log_callback=None):
        log_callback('Rebooting appliance')
        client = self.ssh_client

        old_uptime = client.uptime()
        status, out = client.run_command('reboot')

        wait_for(lambda: client.uptime() < old_uptime, handle_exception=True,
            num_sec=600, message='appliance to reboot', delay=10)

        if wait_for_web_ui:
            self.wait_for_web_ui()

    @logger_wrap("Waiting for web_ui: {}")
    def wait_for_web_ui(self, timeout=900, running=True, log_callback=None):
        """Waits for the web UI to be running / to not be running

        Args:
            timeout: Number of seconds to wait until timeout (default ``600``)
            running: Specifies if we wait for web UI to start or stop (default ``True``)
                     ``True`` == start, ``False`` == stop
        """
        prefix = "" if running else "dis"
        (log_callback or self.log.info)('Waiting for web UI to ' + prefix + 'appear')
        result, wait = wait_for(self._check_appliance_ui_wait_fn, num_sec=timeout,
            fail_condition=not running, delay=10)
        return result

    @logger_wrap("Install VDDK: {}")
    def install_vddk(self, reboot=True, force=False, vddk_url=None, log_callback=None,
                     wait_for_web_ui_after_reboot=False):
        """Install the vddk on a appliance"""

        def log_raise(exception_class, message):
            log_callback(message)
            raise exception_class(message)

        if vddk_url is None:  # fallback to VDDK 5.5
            vddk_url = conf.cfme_data.get("basic_info", {}).get("vddk_url", None).get("v5_5", None)
        if vddk_url is None:
            raise Exception("vddk_url not specified!")

        with self.ssh_client as client:
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

                # install
                log_callback('Installing vddk')
                status, out = client.run_command(
                    'yum -y install {}'.format(filename))
                if status != 0:
                    log_raise(
                        Exception, 'VDDK installation failure (rc: {})\n{}'.format(out, status))

                # verify
                log_callback('Verifying vddk')
                status, out = client.run_command('ldconfig -p | grep vix')
                if len(out) < 2:
                    log_raise(
                        Exception,
                        "Potential installation issue, libraries not detected\n{}".format(out))

                # reboot
                if reboot:
                    self.reboot(log_callback=log_callback,
                                wait_for_web_ui=wait_for_web_ui_after_reboot)
                else:
                    log_callback('A reboot is required before vddk will work')

    @logger_wrap("Install Netapp SDK: {}")
    def install_netapp_sdk(self, sdk_url=None, reboot=False, log_callback=None):
        """Installs the Netapp SDK.

        Args:
            sdk_url: Where the SDK zip file is located? (optional)
            reboot: Whether to reboot the appliance afterwards? (Default False but reboot is needed)
        """

        def log_raise(exception_class, message):
            log_callback(message)
            raise exception_class(message)

        if sdk_url is None:
            try:
                sdk_url = conf.cfme_data['basic_info']['netapp_sdk_url']
            except KeyError:
                raise Exception("cfme_data.yaml/basic_info/netapp_sdk_url is not present!")

        filename = sdk_url.split('/')[-1]
        foldername = os.path.splitext(filename)[0]

        with self.ssh_client as ssh:
            log_callback('Downloading SDK from {}'.format(sdk_url))
            status, out = ssh.run_command(
                'wget {url} -O {file} > /root/unzip.out 2>&1'.format(
                    url=sdk_url, file=filename))
            if status != 0:
                log_raise(Exception, 'Could not download Netapp SDK: {}'.format(out))

            log_callback('Extracting SDK ({})'.format(filename))
            status, out = ssh.run_command(
                'unzip -o -d /var/www/miq/vmdb/lib/ {}'.format(filename))
            if status != 0:
                log_raise(Exception, 'Could not extract Netapp SDK: {}'.format(out))

            path = '/var/www/miq/vmdb/lib/{}/lib/linux-64'.format(foldername)
            # Check if we haven't already added this line
            if ssh.run_command("grep -F '{}' /etc/default/evm".format(path)).rc != 0:
                log_callback('Installing SDK ({})'.format(foldername))
                status, out = ssh.run_command(
                    'echo "export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:{}" >> /etc/default/evm'.format(
                        path))
                if status != 0:
                    log_raise(Exception, 'SDK installation failure ($?={}): {}'.format(status, out))
            else:
                log_callback("Not needed to install, already done")

            log_callback('ldconfig')
            ssh.run_command('ldconfig')

            log_callback('Modifying YAML configuration')
            c_yaml = self.get_yaml_config('vmdb')
            c_yaml['product']['storage'] = True
            self.set_yaml_config('vmdb', c_yaml)

            # To mark that we installed netapp
            ssh.run_command("touch /var/www/miq/vmdb/HAS_NETAPP")

            if reboot:
                self.reboot(log_callback=log_callback)
            else:
                log_callback(
                    'Appliance must be restarted before the netapp functionality can be used.')

    def wait_for_db(self, timeout=600):
        """Waits for appliance database to be ready

        Args:
            timeout: Number of seconds to wait until timeout (default ``180``)
        """
        wait_for(func=lambda: self.is_db_ready,
                 message='appliance.is_db_ready',
                 delay=20,
                 num_sec=timeout)

    def wait_for_ssh(self, timeout=600):
        """Waits for appliance SSH connection to be ready

        Args:
            timeout: Number of seconds to wait until timeout (default ``600``)
        """
        wait_for(func=lambda: self.is_ssh_running,
                 message='appliance.is_ssh_running',
                 delay=5,
                 num_sec=timeout)

    def get_host_address(self):
        try:
            if self.version >= '5.6':
                server = self.get_yaml_config('vmdb').get('server', None)
            else:
                server = self.get_yaml_file('/var/www/miq/vmdb/config/vmdb.yml.db').get(
                    'server', None)
            if server:
                return server.get('host', None)
        except Exception as e:
            logger.exception(e)
            self.log.error('Exception occured while fetching host address')

    def wait_for_host_address(self):
        try:
            wait_for(func=self.get_host_address,
                     fail_condition=None,
                     delay=5,
                     num_sec=120)
            return self.get_host_address()
        except Exception as e:
            logger.exception(e)
            self.log.error('waiting for host address from yaml_config timedout')

    @cached_property
    def db_address(self):
        # pulls the db address from the appliance by default, falling back to the appliance
        # ip address (and issuing a warning) if that fails. methods that set up the internal
        # db should set db_address to something else when they do that
        try:
            db = self.wait_for_host_address()
            if db is None:
                return self.address
            db = db.strip()
            ip_addr = self.ssh_client.run_command('ip address show')
            if db in ip_addr.output or db.startswith('127') or 'localhost' in db:
                # address is local, use the appliance address
                return self.address
            else:
                return db
        except (IOError, KeyError) as exc:
            self.log.error('Unable to pull database address from appliance')
            self.log.exception(exc)
            return self.address

    @cached_property
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
        result = self.db_ssh_client.run_command(db_check_command)
        return result.rc == 0

    @property
    def db_has_database(self):
        db_check_command = ('psql -U postgres -t  -c "SELECT datname FROM pg_database '
            'WHERE datname LIKE \'vmdb_%\';" postgres | grep -q vmdb_production')
        result = self.db_ssh_client.run_command(db_check_command)
        return result.rc == 0

    @property
    def db_has_tables(self):
        db_check_command = ('psql -U postgres -t  -c "SELECT * FROM information_schema.tables '
            'WHERE table_schema = \'public\';" vmdb_production | grep -q vmdb_production')
        result = self.db_ssh_client.run_command(db_check_command)
        return result.rc == 0

    @property
    def is_ssh_running(self):
        return net_check(ports.SSH, self.hostname, force=True)

    @property
    def has_cli(self):
        if self.ssh_client.run_command('ls -l /bin/appliance_console_cli')[0] == 0:
            return True
        else:
            return False

    @cached_property
    def build_datetime(self):
        datetime = self.ssh_client.get_build_datetime()
        return datetime

    @cached_property
    def build_date(self):
        date = self.ssh_client.get_build_date()
        return date

    @cached_property
    def is_downstream(self):
        return self.ssh_client.is_appliance_downstream()

    def has_netapp(self):
        return self.ssh_client.appliance_has_netapp()

    @cached_property
    def guid(self):
        result = self.ssh_client.run_command('cat /var/www/miq/vmdb/GUID')
        return result.output

    @cached_property
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

    def server_region_string(self):
        r = self.server_region()
        if self.is_downstream:
            return "CFME Region: Region {} [{}]".format(r, r)
        else:
            return "ManageIQ Region: Region {} [{}]".format(r, r)

    @cached_property
    def zone_description(self):
        return db_queries.get_zone_description(self.server_zone_id(), db=self.db)

    @cached_property
    def host_id(self, hostname):
        return db_queries.get_host_id(hostname, db=self.db)

    def get_yaml_config(self, config_name):
        if config_name == 'vmdb':
            writeout = self.ssh_client.run_rails_command(
                '"File.open(\'/tmp/yam_dump.yaml\', \'w\') '
                '{|f| f.write(Settings.to_hash.deep_stringify_keys.to_yaml) }"'
            )
            if writeout.rc:
                logger.error("Config couldn't be found")
                logger.error(writeout.output)
                raise Exception('Error obtaining config')
            base_data = self.ssh_client.run_command('cat /tmp/yam_dump.yaml')
            if base_data.rc:
                logger.error("Config couldn't be found")
                logger.error(base_data.output)
                raise Exception('Error obtaining config')
            try:
                return yaml.load(base_data.output)
            except:
                logger.debug(base_data.output)
                raise
        else:
            raise Exception('Only [vmdb] config is allowed from 5.6+')

    def set_yaml_config(self, config_name, data_dict):
        if config_name == 'vmdb':
            temp_yaml = NamedTemporaryFile()
            dest_yaml = '/tmp/conf.yaml'
            yaml.dump(data_dict, temp_yaml, default_flow_style=False)
            self.ssh_client.put_file(temp_yaml.name, dest_yaml)
            # Build and send ruby script
            dest_ruby = '/tmp/set_conf.rb'

            ruby_template = data_path.join('utils', 'cfmedb_set_config.rbt')
            ruby_replacements = {
                'config_file': dest_yaml
            }
            temp_ruby = load_data_file(ruby_template.strpath, ruby_replacements)
            self.ssh_client.put_file(temp_ruby.name, dest_ruby)

            # Run it
            if self.ssh_client.run_rails_command(dest_ruby):
                self.server_details_changed()
            else:
                raise Exception('Unable to set config')
        else:
            raise Exception('Only [vmdb] config is allowed from 5.6+')

    def get_yaml_file(self, yaml_path):
        """Get (and parse) a yaml file from the appliance, returning a python data structure"""
        ret = self.ssh_client.run_command('cat {}'.format(yaml_path))
        if ret.rc == 0:
            # Let yaml throw the exceptions here if yaml_path wasn't actually a yaml
            return yaml.load(ret.output)
        else:
            # 2 = errno.ENOENT
            raise IOError(2, 'Remote yaml not found or permission denied')

    def set_session_timeout(self, timeout=86400, quiet=True):
        """Sets the timeout of UI timeout.

        Args:
            timeout: Timeout in seconds
            quiet: Whether to ignore any errors
        """
        try:
            vmdb_config = self.get_yaml_config("vmdb")
            if vmdb_config["session"]["timeout"] != timeout:
                vmdb_config["session"]["timeout"] = timeout
                self.set_yaml_config("vmdb", vmdb_config)
        except Exception as ex:
            logger.error('Setting session timeout failed:')
            logger.exception(ex)
            if not quiet:
                raise

    def delete_all_providers(self):
        for prov in self.rest_api.collections.providers:
            prov.action.delete()

    def reset_automate_model(self):
        with self.ssh_client as ssh_client:
            ssh_client.run_rake_command("evm:automate:reset")

    def server_details_changed(self):
        clear_property_cache(self, 'configuration_details', 'zone_description')


@navigator.register(IPAppliance)
class LoggedIn(CFMENavigateStep):
    def step(self):
        from cfme.login import login
        from utils.browser import browser
        browser()
        login(store.user)


@navigator.register(IPAppliance)
class Dashboard(CFMENavigateStep):
    prerequisite = NavigateToSibling('LoggedIn')

    def am_i_here(self):
        from cfme.web_ui.menu import nav
        if self.obj.version < "5.6.0.1":
            nav.CURRENT_TOP_MENU = "//ul[@id='maintab']/li[not(contains(@class, 'drop'))]/a[2]"
        else:
            nav.CURRENT_TOP_MENU = "{}{}".format(nav.ROOT, nav.ACTIVE_LEV)
        nav.is_page_active('Dashboard')

    def step(self):
        from cfme.web_ui.menu import nav
        nav._nav_to_fn('Cloud Intel', 'Dashboard')(None)


class Appliance(IPAppliance):
    """Appliance represents an already provisioned cfme appliance vm

    Args:
        provider_name: Name of the provider this appliance is running under
        vm_name: Name of the VM this appliance is running as
        browser_steal: Setting of the browser_steal attribute.
    """

    _default_name = 'EVM'

    def __init__(self, provider_name, vm_name, browser_steal=False, container=None):
        """Initializes a deployed appliance VM
        """
        super(Appliance, self).__init__(browser_steal=browser_steal, container=None)
        self.name = Appliance._default_name

        self._provider_name = provider_name
        self.vmname = vm_name

    def __eq__(self, other):
        return isinstance(other, type(self)) and (
            self.vmname == other.vmname and self._provider_name == other._provider_name)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return int(hashlib.md5("{}@{}".format(self.vmname, self._provider_name)).hexdigest(), 16)

    @property
    def ipapp(self):
        # For backwards compat
        return self

    @cached_property
    def provider(self):
        """
        Note:
            Cannot be cached because provider object is unpickable.
        """
        from utils.providers import get_mgmt
        return get_mgmt(self._provider_name)

    @property
    def vm_name(self):
        """ VM's name of the appliance on the provider """
        return self.vmname

    @cached_property
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
        return str(ec)

    def _custom_configure(self, **kwargs):
        log_callback = kwargs.pop(
            "log_callback",
            lambda msg: logger.info("Custom configure %s: %s", self.vmname, msg))
        region = kwargs.get('region', 0)
        db_address = kwargs.get('db_address', None)
        key_address = kwargs.get('key_address', None)
        db_username = kwargs.get('db_username', None)
        db_password = kwargs.get('ssh_password', None)
        ssh_password = kwargs.get('ssh_password', None)
        db_name = kwargs.get('db_name', None)

        if kwargs.get('fix_ntp_clock', True) is True:
            self.fix_ntp_clock(log_callback=log_callback)
        if kwargs.get('db_address', None) is None:
            self.enable_internal_db(
                region, key_address, db_password, ssh_password, log_callback=log_callback)
        else:
            self.enable_external_db(
                db_address, region, db_name, db_username, db_password,
                log_callback=log_callback)
        self.wait_for_web_ui(timeout=1800, log_callback=log_callback)
        if kwargs.get('loosen_pgssl', True) is True:
            self.loosen_pgssl(log_callback=log_callback)

        name_to_set = kwargs.get('name_to_set', None)
        if name_to_set is not None and name_to_set != self.name:
            self.rename(name_to_set)
            self.restart_evm_service(log_callback=log_callback)
            self.wait_for_web_ui(log_callback=log_callback)

    @logger_wrap("Configure Appliance: {}")
    def configure(self, setup_fleece=False, log_callback=None, **kwargs):
        """Configures appliance - database setup, rename, ntp sync

        Utility method to make things easier.

        Args:
            db_address: Address of external database if set, internal database if ``None``
                        (default ``None``)
            name_to_set: Name to set the appliance name to if not ``None`` (default ``None``)
            region: Number to assign to region (default ``0``)
            fix_ntp_clock: Fixes appliance time if ``True`` (default ``True``)
            loosen_pgssl: Loosens postgres connections if ``True`` (default ``True``)
            key_address: Fetch encryption key from this address if set, generate a new key if
                         ``None`` (default ``None``)

        """
        log_callback("Configuring appliance {} on {}".format(self.vmname, self._provider_name))
        if kwargs:
            with self:
                self._custom_configure(**kwargs)
        else:
            # Defer to the IPAppliance.
            super(Appliance, self).configure(log_callback=log_callback)
        # And do configure the fleecing if requested
        if setup_fleece:
            self.configure_fleecing(log_callback=log_callback)

    @logger_wrap("Configure fleecing: {}")
    def configure_fleecing(self, log_callback=None):
        from cfme.configure.configuration import set_server_roles, get_server_roles
        from utils.providers import setup_provider
        with self(browser_steal=True):
            if self.is_on_vsphere:
                self.install_vddk(reboot=True, log_callback=log_callback)
                self.wait_for_web_ui(log_callback=log_callback)

            if self.is_on_rhev:
                self.add_rhev_direct_lun_disk()

            log_callback('Enabling smart proxy role...')
            roles = get_server_roles()
            if not roles["smartproxy"]:
                roles["smartproxy"] = True
                set_server_roles(**roles)
                # web ui crashes
                if str(self.version).startswith("5.2.5") or str(self.version).startswith("5.5"):
                    try:
                        self.wait_for_web_ui(timeout=300, running=False)
                    except:
                        pass
                    self.wait_for_web_ui(running=True)

            # add provider
            log_callback('Setting up provider...')
            setup_provider(self._provider_name)

            # credential hosts
            log_callback('Credentialing hosts...')
            if not RUNNING_UNDER_SPROUT:
                from utils.hosts import setup_providers_hosts_credentials
            setup_providers_hosts_credentials(self._provider_name, ignore_errors=True)

            # if rhev, set relationship
            if self.is_on_rhev:
                from cfme.infrastructure.virtual_machines import Vm  # For Vm.CfmeRelationship
                log_callback('Setting up CFME VM relationship...')
                from cfme.common.vm import VM
                from utils.providers import get_crud
                vm = VM.factory(self.vm_name, get_crud(self._provider_name))
                cfme_rel = Vm.CfmeRelationship(vm)
                cfme_rel.set_relationship(str(self.server_name()), self.server_id())

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
        vmdb_config = self.get_yaml_config('vmdb', self.db)
        vmdb_config['server']['name'] = new_name
        self.set_yaml_config('vmdb', vmdb_config, self.address)
        self.name = new_name

    def destroy(self):
        """Destroys the VM this appliance is running as
        """
        if isinstance(self.provider, RHEVMSystem):
            # if rhev, try to remove direct_lun just in case it is detach
            self.remove_rhev_direct_lun_disk()
        self.provider.delete_vm(self.vm_name)

    def stop(self):
        """Stops the VM this appliance is running as
        """
        self.provider.stop_vm(self.vm_name)
        self.provider.wait_vm_stopped(self.vm_name)

    def start(self):
        """Starts the VM this appliance is running as
        """
        self.provider.start_vm(self.vm_name)
        self.provider.wait_vm_running(self.vm_name)

    def templatize(self, seal=True):
        """Marks the appliance as a template. Destroys the original VM in the process.

        By default it runs the sealing process. If you have done it differently, you can opt out.

        Args:
            seal: Whether to run the sealing process (making the VM 'universal').
        """
        if seal:
            if not self.is_running:
                self.start()
            self.seal_for_templatizing()
            self.stop()
        else:
            if self.is_running:
                self.stop()
        self.provider.mark_as_template(self.vm_name)

    @property
    def is_running(self):
        return self.provider.is_vm_running(self.vm_name)

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
        self.wait_for_ssh()
        try:
            self.provider.connect_direct_lun_to_appliance(self.vm_name, False)
        except Exception as e:
            log_callback("Appliance {} failed to connect RHEV direct LUN.".format(self.vm_name))
            log_callback(str(e))
            raise

    @logger_wrap("Remove RHEV LUN: {}")
    def remove_rhev_direct_lun_disk(self, log_callback=None):
        if not self.is_on_rhev:
            msg = "appliance {} NOT on rhev, unable to disconnect direct_lun".format(self.vmname)
            log_callback(msg)
            raise ApplianceException(msg)
        log_callback('Removing RHEV direct_lun hook...')
        self.wait_for_ssh()
        try:
            self.provider.connect_direct_lun_to_appliance(self.vm_name, True)
        except Exception as e:
            log_callback("Appliance {} failed to connect RHEV direct LUN.".format(self.vm_name))
            log_callback(str(e))
            raise


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
        E.g.: if there is no template for 5.5.5.1 but there is 5.5.5.3, it will be used instead.
        If both template name and version are specified, template name takes priority.

    Args:
        version: version of appliance to provision
        vm_name_prefix: name prefix to use when deploying the appliance vm

    Returns: Unconfigured appliance; instance of :py:class:`Appliance`

    Usage:
        my_appliance = provision_appliance('5.5.1.8', 'my_tests')
        my_appliance.fix_ntp_clock()
        ...other configuration...
        my_appliance.enable_internal_db()
        my_appliance.wait_for_web_ui()
        or
        my_appliance = provision_appliance('5.5.1.8', 'my_tests')
        my_appliance.configure()
    """

    def _generate_vm_name():
        if version is not None:
            version_digits = ''.join([letter for letter in version if letter.isdigit()])
            return '{}_{}_{}'.format(
                vm_name_prefix, version_digits, fauxfactory.gen_alphanumeric(8))
        else:
            return '{}_{}'.format(vm_name_prefix, fauxfactory.gen_alphanumeric(8))

    def _get_latest_template():
        from utils import trackerbot
        api = trackerbot.api()
        stream = get_stream(version)
        template_data = trackerbot.latest_template(api, stream, provider_name)
        return template_data.get('latest_template', None)

    if provider_name is None:
        provider_name = conf.cfme_data.get('appliance_provisioning', {})['default_provider']

    if template is not None:
        template_name = template
    elif version is not None:
        templates_by_version = conf.cfme_data.get('appliance_provisioning', {}).get('versions', {})
        try:
            template_name = templates_by_version[version]
        except KeyError:
            # We try to get the latest template from the same stream - if trackerbot is set up
            if conf.env.get('trackerbot', {}):
                template_name = _get_latest_template()
                if not template_name:
                    raise ApplianceException('No template found for stream {} on provider {}'
                        .format(get_stream(version), provider_name))
                logger.warning('No template found matching version %s, using %s instead.',
                    version, template_name)
            else:
                raise ApplianceException('No template found matching version {}'.format(version))
    else:
        raise ApplianceException('Either version or template name must be specified')

    prov_data = conf.cfme_data.get('management_systems', {})[provider_name]
    from utils.providers import get_mgmt
    provider = get_mgmt(provider_name)
    if not vm_name:
        vm_name = _generate_vm_name()

    deploy_args = {}
    deploy_args['vm_name'] = vm_name

    if prov_data['type'] == 'rhevm':
        deploy_args['cluster'] = prov_data['default_cluster']

    if prov_data["type"] == "virtualcenter":
        if "allowed_datastores" in prov_data:
            deploy_args["allowed_datastores"] = prov_data["allowed_datastores"]

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


class ApplianceStack(LocalStack):

    def push(self, obj):
        was_before = self.top
        super(ApplianceStack, self).push(obj)

        logger.info("Pushed appliance {} on stack (was {} before) ".format(
            obj.address, getattr(was_before, 'address', 'empty')))
        if obj.browser_steal:
            from utils import browser
            browser.start()

    def pop(self):
        was_before = super(ApplianceStack, self).pop()
        current = self.top
        logger.info(
            "Popped appliance {} from the stack (now there is {})".format(
                was_before.address, getattr(current, 'address', 'empty')))
        if was_before.browser_steal:
            from utils import browser
            browser.start()
        return was_before

stack = ApplianceStack()


def get_or_create_current_appliance():
    if stack.top is None:
        base_url = conf.env['base_url']
        if base_url is None or str(base_url.lower()) == 'none':
            raise ValueError('No IP address specified! Specified: {}'.format(repr(base_url)))
        stack.push(IPAppliance(urlparse(base_url), container=conf.env.get('container', None)))
    return stack.top

current_appliance = LocalProxy(get_or_create_current_appliance)


class CurrentAppliance(object):
    def __get__(self, instance, owner):
        return get_or_create_current_appliance()


class Navigatable(object):

    appliance = CurrentAppliance()

    def __init__(self, appliance=None):
        self.appliance = appliance or get_or_create_current_appliance()
