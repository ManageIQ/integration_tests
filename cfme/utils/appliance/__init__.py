import json
import logging
import os
import re
import socket
import traceback
import warnings
from copy import copy
from datetime import datetime
from time import sleep
from time import time
from urllib.parse import urlparse

import attr
import dateutil.parser
import fauxfactory
import pytest
import pytz
import requests
import sentaku
from cached_property import cached_property
from debtcollector import removals
from manageiq_client.api import APIException
from manageiq_client.api import ManageIQClient as VanillaMiqApi
from urllib3.exceptions import ConnectionError
from werkzeug.local import LocalProxy
from werkzeug.local import LocalStack
from wrapanapi import VmState
from wrapanapi.exceptions import VMInstanceNotFound

from cfme.fixtures import ui_coverage
from cfme.fixtures.pytest_store import store
from cfme.utils import clear_property_cache
from cfme.utils import conf
from cfme.utils import ports
from cfme.utils import ssh
from cfme.utils.appliance import console
from cfme.utils.appliance.db import ApplianceDB
from cfme.utils.appliance.implementations.rest import ViaREST
from cfme.utils.appliance.implementations.ssui import ViaSSUI
from cfme.utils.appliance.implementations.ui import ViaUI
from cfme.utils.appliance.services import SystemdException
from cfme.utils.appliance.services import SystemdService
from cfme.utils.log import create_sublogger
from cfme.utils.log import logger
from cfme.utils.log import logger_wrap
from cfme.utils.net import is_pingable
from cfme.utils.net import net_check
from cfme.utils.net import resolve_hostname
from cfme.utils.path import conf_path
from cfme.utils.path import patches_path
from cfme.utils.path import scripts_path
from cfme.utils.ssh import SSHTail
from cfme.utils.version import get_stream
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

RUNNING_UNDER_SPROUT = os.environ.get("RUNNING_UNDER_SPROUT", "false") != "false"
# EMS types recognized by IP or credentials
RECOGNIZED_BY_IP = [
    "InfraManager", "ContainerManager", "Openstack::CloudManager", "ConfigurationManager",
    "AutomationManager"
]
RECOGNIZED_BY_CREDS = ["CloudManager", "Nuage::NetworkManager"]

# A helper for the IDs
SEQ_FACT = 1e12

EMBEDDED_PROVIDERS = ('Embedded Ansible', )


def _current_miqqe_version():
    """Parses MiqQE JS patch version from the patch file

    Returns: Version as int
    """
    with patches_path.join('miq_application.js.diff').open("r") as f:
        match = re.search(r"MiqQE_version = (\d+);", f.read(), flags=0)
    version = int(match.group(1))
    return version


current_miqqe_version = _current_miqqe_version()


class MiqApi(VanillaMiqApi):
    def get_entity_by_href(self, href):
        """Parses the collections"""
        parsed = urlparse(href)
        # TODO: Check the netloc, scheme
        path = [step for step in parsed.path.split('/') if step]
        # Drop the /api
        path = path[1:]
        collection = getattr(self.collections, path.pop(0))
        entity = collection(int(path.pop(0)))
        if path:
            raise ValueError(f'Subcollections not supported! ({parsed.path})')
        return entity


class ApplianceException(Exception):
    pass


class IPAppliance:
    """IPAppliance represents an already provisioned cfme appliance whos provider is unknown
    but who has an IP address. This has a lot of core functionality that Appliance uses, since
    it knows both the provider, vm_name and can there for derive the IP address.

    Args:
        hostname: The IP address  or host name of the provider
        ui_protocol: The protocol used in the URL
        ui_port: The port where the UI runs.
        browser_steal: If True then then current browser is killed and the new appliance
            is used to generate a new session.
        container: If the appliance is running as a container or as a pod, specifies its name.
        project: openshift's project where the appliance is deployed
        openshift_creds: If the appliance runs as a project on openshift, provides credentials for
            the openshift host so the framework can interact with the project.
        db_host: If the database is located somewhere else than on the appliance itself, specify
            the host here.
        db_port: Database port.
        ssh_port: SSH port.
    """
    _nav_steps = {}

    appliance_console = console.ApplianceConsole.declare()
    appliance_console_cli = console.ApplianceConsoleCli.declare()
    auditd = SystemdService.declare(unit_name='auditd')
    chronyd = SystemdService.declare(unit_name='chronyd')
    collectd = SystemdService.declare(unit_name='collectd')
    db = ApplianceDB.declare()
    evminit = SystemdService.declare(unit_name='evminit')
    evmserverd = SystemdService.declare(unit_name='evmserverd')
    evm_failover_monitor = SystemdService.declare(unit_name='evm-failover-monitor')
    firewalld = SystemdService.declare(unit_name='firewalld')
    httpd = SystemdService.declare(unit_name='httpd')
    nginx = SystemdService.declare(unit_name='nginx')
    rabbitmq_server = SystemdService.declare(unit_name='rabbitmq-server')
    repmgr = SystemdService.declare()
    sssd = SystemdService.declare(unit_name='sssd')
    sshd = SystemdService.declare(unit_name='sshd')
    supervisord = SystemdService.declare(unit_name='supervisord')

    CONFIG_MAPPING = {
        'hostname': 'hostname',
        'ui_protocol': 'ui_protocol',
        'ui_port': 'ui_port',
        'browser_steal': 'browser_steal',
        'container': 'container',
        'pod': 'container',
        'openshift_creds': 'openshift_creds',
        'is_dev': 'is_dev',
        'db_host': 'db_host',
        'db_port': 'db_port',
        'ssh_port': 'ssh_port',
        'project': 'project',
        'version': 'version',
    }
    CONFIG_NONGLOBAL = {'hostname'}
    PROTOCOL_PORT_MAPPING = {'http': 80, 'https': 443}
    CONF_FILES = {
        'upstream_templates': '/var/www/miq/system/TEMPLATE',
        'downstream_templates': '/opt/rh/cfme-appliance/TEMPLATE',
        'pam_httpd_auth': '/etc/pam.d/httpd-auth',
        'httpd_remote_user': '/etc/httpd/conf.d/manageiq-remote-user.conf',
        'httpd_ext_auth': '/etc/httpd/conf.d/manageiq-external-auth.conf',
        'openldap': '/etc/openldap/ldap.conf',
        'sssd': '/etc/sssd/sssd.conf'
    }

    @cached_property
    def db_service(self):
        return SystemdService(self, unit_name=self.db.service_name)

    @cached_property
    def repmgr(self):
        return VersionPicker({
            '5.10': SystemdService(self, unit_name='rh-postgresql95-repmgr'),
            '5.11': SystemdService(self, unit_name='repmgr10')}
        ).pick(self.version)

    @property
    def as_json(self):
        """Dumps the arguments that can create this appliance as a JSON. None values are ignored."""
        def _version_tostr(x):
            if isinstance(x, Version):
                return str(x)
            else:
                return x
        return json.dumps({
            k: _version_tostr(getattr(self, k))
            for k in set(self.CONFIG_MAPPING.values())
            if k in self.__dict__})

    @classmethod
    def from_json(cls, json_string):
        return cls(**json.loads(json_string))

    def __init__(
            self, hostname, ui_protocol='https', ui_port=None, browser_steal=False, project=None,
            container=None, openshift_creds=None, db_host=None, db_port=None, ssh_port=None,
            is_dev=False, version=None,
    ):
        if not isinstance(hostname, str):
            raise TypeError('Appliance\'s hostname must be a string!')
        self.hostname = hostname
        if ui_protocol not in self.PROTOCOL_PORT_MAPPING:
            raise TypeError(
                'Wrong protocol {!r} passed, expected {!r}'.format(
                    ui_protocol, list(self.PROTOCOL_PORT_MAPPING.keys())))
        self.ui_protocol = ui_protocol
        self.ui_port = ui_port or self.PROTOCOL_PORT_MAPPING[ui_protocol]
        self.ssh_port = ssh_port or ports.SSH
        self.db_port = db_port or ports.DB
        self.db_host = db_host
        self.browser = ViaUI(owner=self)
        self.ssui = ViaSSUI(owner=self)
        self.rest_context = ViaREST(owner=self)
        self.rest_context.strict_calls = False
        self.context = MiqImplementationContext.from_instances(
            [self.browser, self.ssui, self.rest_context])

        from cfme.modeling.base import EntityCollections
        self.collections = EntityCollections.for_appliance(self)
        self.browser_steal = browser_steal
        self.container = container
        self.project = project
        self.openshift_creds = openshift_creds or {}
        self.is_dev = is_dev
        self._user = None

        if self.openshift_creds:
            self.is_pod = True
        else:
            self.is_pod = False
        # only set when given so we can defer to the rest api via the cached property
        self._version = version

    def unregister(self):
        """ unregisters appliance from RHSM/SAT6 """
        with self.ssh_client as ssh_client:
            ssh_client.run_command('subscription-manager remove --all')
            ssh_client.run_command('subscription-manager unregister')
            ssh_client.run_command('subscription-manager clean')
            ssh_client.run_command('mv -f /etc/rhsm/rhsm.conf.kat-backup /etc/rhsm/rhsm.conf')
            ssh_client.run_command('rpm -qa | grep katello-ca-consumer | xargs rpm -e')

    def is_registration_complete(self, used_repo_or_channel):
        """ Checks if an appliance has the correct repos enabled with RHSM or SAT6 """
        result = self.ssh_client.run_command('yum repolist enabled')
        return all(repo in result.output for repo in used_repo_or_channel.split(' '))

    @property
    def default_zone(self):
        return self.appliance.server.zone

    @property
    def name(self):
        """Appliance name from advanced settings, equivalent to master server name"""
        try:
            return self.advanced_settings['server']['name']
        except KeyError:
            logger.exception('Appliance name attribute not where it was expected in %r',
                             self.advanced_settings.get('server'))
            raise ApplianceException('Failed to find appliance server name key in settings')

    @property
    def server(self):
        sid = self._rest_api_server.id
        return self.collections.servers.instantiate(sid=sid)

    @property
    def _rest_api_server(self):
        shref = self.appliance.rest_api.server_info['server_href']
        results = self.appliance.rest_api.collections.servers.all
        server, = (r for r in results if r.href == shref)
        return server

    @property
    def user(self):
        from cfme.base.credential import Credential
        if self._user is None:
            # Admin by default
            username = conf.credentials['default']['username']
            password = conf.credentials['default']['password']
            logger.info(
                '%r.user was set to None before, therefore generating an admin user: %s/%s',
                self, username, password)
            cred = Credential(principal=username, secret=password)
            user = self.collections.users.instantiate(
                credential=cred, name='Administrator'
            )
            self._user = user
        return self._user

    @user.setter
    def user(self, user_object):
        if user_object is None:
            logger.info('%r.user set to None, will be set to admin on next access', self)
        self._user = user_object

    @property
    def appliance(self):
        return self

    @property
    def configured(self):
        """"Return boolean indicating if the appliance is configured """
        return self.db_service.enabled and self.evmserverd.enabled

    def __repr__(self):
        # TODO: Put something better here. This solves the purpose temporarily.
        return '{}.from_json({!r})'.format(type(self).__name__, self.as_json)

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

    def _screenshot_capture_at_context_leave(self, exc_type, exc_val, exc_tb):

        try:
            from cfme.fixtures.artifactor_plugin import fire_art_hook
            from pytest import config
            from cfme.fixtures.pytest_store import store
        except ImportError:
            logger.info('Not inside pytest run, ignoring')
            return

        if (
                exc_type is not None and not RUNNING_UNDER_SPROUT):
            from cfme.utils.browser import take_screenshot
            logger.info("Before we pop this appliance, a screenshot and a traceback will be taken.")
            ss, ss_error = take_screenshot()
            full_tb = "".join(traceback.format_tb(exc_tb))
            short_tb = "{}: {}".format(exc_type.__name__, str(exc_val))
            full_tb = f"{full_tb}\n{short_tb}"

            g_id = fauxfactory.gen_alpha(length=30, start="appliance-cm-screenshot-")

            fire_art_hook(
                config, 'filedump',
                slaveid=store.slaveid,
                description="Appliance CM error traceback", contents=full_tb, file_type="traceback",
                display_type="danger", display_glyph="align-justify", group_id=g_id)

            if ss:
                fire_art_hook(
                    config, 'filedump',
                    slaveid=store.slaveid, description="Appliance CM error screenshot",
                    file_type="screenshot", mode="wb", contents_base64=True, contents=ss,
                    display_glyph="camera", group_id=g_id)
            if ss_error:
                fire_art_hook(
                    config, 'filedump',
                    slaveid=store.slaveid,
                    description="Appliance CM error screenshot failure", mode="w",
                    contents_base64=False, contents=ss_error, display_type="danger", group_id=g_id)
        elif exc_type is not None:
            logger.info("Error happened but we are not inside a test run so no screenshot now.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._screenshot_capture_at_context_leave(exc_type, exc_val, exc_tb)
        except Exception:
            # repr is used in order to avoid having the appliance object in the log record
            logger.exception("taking a screenshot for %s failed", repr(self))
        finally:
            assert stack.pop() is self, 'appliance stack inconsistent'

    def __eq__(self, other):
        return isinstance(other, IPAppliance) and self.hostname == other.hostname

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.hostname)

    @cached_property
    def rest_logger(self):
        return create_sublogger('rest-api')

    def set_rails_deprecation(self, filename='production.rb', behavior=':notify'):
        """Update config/environments/production.rb to control rails deprecation message behavior

        Args:
            file (str): filename to set behavior in - should be production.rb or development.rb
            behavior (str): formatted string for the desired behavior, common are:
                            :notify, :log, :raise
        """
        if filename not in ['production.rb', 'development.rb']:
            logger.error('Invalid file passed for setting rails deprecation behavior, skipping')
            return False
        file = os.path.join('/var/www/miq/vmdb/config/environments', filename)
        with self.ssh_client as client:
            # use sed to replace config.active_support.deprecation = <current> with `behavior`
            result = client.run_command(
                r'sed -i "s/config\.active_support\.deprecation = .*/'
                r'config\.active_support\.deprecation = {}/gm" {}'
                .format(behavior, file)
            )
            # sed returns 0 even if the match didn't work, so checking success doesn't really help
            # it will return non-0 if the file wasn't found for some reason

        return result.success

    # Configuration methods
    @logger_wrap("Configure IPAppliance: {}")
    def configure(self, log_callback=None, **kwargs):
        """Configures appliance - database setup, rename, ntp sync

        Utility method to make things easier.

        Note:
            db_address, name_to_set are not used currently.

        Args:
            db_address: Address of external database if set, internal database if ``None``
                        (default ``None``)
            name_to_set: Name to set the appliance name to if not ``None`` (default ``None``)
            region: Number to assign to region (default ``0``)
            fix_ntp_clock: Fixes appliance time if ``True`` (default ``True``)
            key_address: Fetch encryption key from this address if set, generate a new key if
                         ``None`` (default ``None``)
            on_openstack: If appliance is running on Openstack provider (default ``False``)
            on_gce: If appliance is running on GCE provider (default ``False``)
            rails_deprecations: string value for .config.active_support.deprecation in
                                production.rb. Default productization is ``:notify``
                                QE default is ``:log``
                                To hard-fault on rails deprecations, use ``:raise``
        """

        log_callback(f"Configuring appliance {self.hostname}")
        fix_ntp_clock = kwargs.pop('fix_ntp_clock', True)
        region = kwargs.pop('region', 0)
        key_address = kwargs.pop('key_address', None)
        db_address = kwargs.pop('db_address', None)
        on_gce = kwargs.pop('on_gce', False)
        on_openstack = kwargs.pop('on_openstack', False)
        rails_deprecations = kwargs.pop('rails_deprecations', ':log')
        ssh_timeout = kwargs.pop('timeout', 600)
        with self as ipapp:
            ipapp.wait_for_ssh(timeout=ssh_timeout)

            # Debugging - ifcfg-eth0 overwritten by unknown process
            # Rules are permanent and will be reloade after machine reboot
            with self.ssh_client as ssh_client:
                ssh_client.run_command(
                    "cp -pr /etc/sysconfig/network-scripts/ifcfg-eth0 /var/tmp", ensure_host=True)
                ssh_client.run_command(
                    "echo '-w /etc/sysconfig/network-scripts/ifcfg-eth0 -p wa' >> "
                    "/etc/audit/rules.d/audit.rules", ensure_host=True)

            with self.ssh_client as ssh_client:
                self.httpd.daemon_reload()
                # cannot restart through systemctl
                ssh_client.run_command('service auditd restart', ensure_host=True)

            ipapp.wait_for_ssh()

            self.set_rails_deprecation(behavior=rails_deprecations)

            # TODO: Handle external DB setup
            # This is workaround for appliances to use only one disk for the VMDB
            # If they have been provisioned with a second disk in the infra,
            # 'self.unpartitioned_disks' should exist and therefore this won't run.
            if self.is_downstream and not self.unpartitioned_disks:
                self.db.create_db_lvm()
            if on_openstack:
                self.set_resolvable_hostname(log_callback=log_callback)
            if db_address:
                self.db_host = db_address

            self.db.setup(region=region, key_address=key_address,
                          db_address=db_address, is_pod=self.is_pod)

            if on_gce:
                # evm serverd does not auto start on GCE instance..
                self.evmserverd.start(log_callback=log_callback)
            self.evmserverd.wait_for_running(timeout=1200)

            # Some conditionally ran items require the evm service be
            # restarted:
            restart_evm = False
            self.wait_for_miq_ready(log_callback=log_callback)
            if self.version < '5.11':
                self.configure_vm_console_cert(log_callback=log_callback)
                restart_evm = True

            if fix_ntp_clock and not self.is_pod:
                self.set_ntp_sources(log_callback=log_callback)
                restart_evm = True

            if restart_evm:
                self.evmserverd.restart(log_callback=log_callback)
                self.wait_for_miq_ready(num_sec=1800, log_callback=log_callback)

    def configure_gce(self, log_callback=None):
        # Force use of IPAppliance's configure method
        return IPAppliance.configure(self, on_gce=True)

    def seal_for_templatizing(self):
        """Prepares the VM to be "generalized" for saving as a template."""
        with self.ssh_client as ssh_client:
            # Seals the VM in order to work when spawned again.
            ssh_client.run_command("rm -rf /etc/ssh/ssh_host_*", ensure_host=True)
            if ssh_client.run_command(
                    "grep '^HOSTNAME' /etc/sysconfig/network", ensure_host=True).success:
                # Replace it
                ssh_client.run_command(
                    "sed -i -r -e 's/^HOSTNAME=.*$/HOSTNAME=localhost.localdomain/' "
                    "/etc/sysconfig/network", ensure_host=True)
            else:
                # Set it
                ssh_client.run_command(
                    "echo HOSTNAME=localhost.localdomain >> /etc/sysconfig/network",
                    ensure_host=True)
            # clear any set hostname from /etc/hosts
            self.remove_resolvable_hostname()
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
            self.evmserverd.stop()
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

    @cached_property
    def password_gem(self):
        return VersionPicker({
            Version.lowest(): 'MiqPassword',
            '5.11': 'ManageIQ::Password'
        }).pick(self.version)

    def _encrypt_string(self, string):
        try:
            # Let's not log passwords
            logging.disable(logging.CRITICAL)
            result = self.ssh_client.run_rails_command(
                f'"puts {self.password_gem}.encrypt(\'{string}\')"'
            )
            return result.output.strip()
        finally:
            logging.disable(logging.NOTSET)

    @property
    def managed_provider_names(self):
        """Returns a list of names for all providers configured on the appliance

        Note:
            Unlike ``managed_known_providers``, this will also return names of providers that were
            not recognized, but are present.
        """
        known_ems_list = []
        for ems in self.rest_api.collections.providers:
            if not any(
                    p_type in ems['type'] for p_type in RECOGNIZED_BY_IP + RECOGNIZED_BY_CREDS):
                continue
            known_ems_list.append(ems['name'])
        return known_ems_list

    @property
    def managed_known_providers(self):
        """Returns a set of provider crud objects of known providers managed by this appliance

        Note:
            Recognized by name only.
        """
        from cfme.utils.providers import list_providers
        prov_cruds = list_providers(use_global_filters=False, appliance=self)

        found_cruds = set()
        unrecognized_ems_names = set()
        for ems_name in self.managed_provider_names:
            if ems_name in EMBEDDED_PROVIDERS:
                # ignore embedded pre-configured providers
                continue
            for prov in prov_cruds:
                # Name check is authoritative and the only proper way to recognize a known provider
                # Match either by exact name or by child provider name, e.g., 'XXX Network Manager'
                if ems_name == prov.name or re.match(f'^{prov.name} [A-Za-z]+ Manager$', ems_name):
                    found_cruds.add(prov)
                    break
            else:
                unrecognized_ems_names.add(ems_name)
        if unrecognized_ems_names:
            self.log.warning(
                "Unrecognized managed providers: {}".format(', '.join(unrecognized_ems_names)))
        return list(found_cruds)

    @classmethod
    def from_url(cls, url, **kwargs):
        """Create an appliance instance from a URL.

        Supported format using a simple regexp expression:
        ``(https?://)?hostname_or_ip(:port)?/?``

        Args:
            url: URL to be parsed from
            **kwargs: For setting and overriding the params parsed from the URL

        Returns:
            A :py:class:`IPAppliance` instance.
        """
        if not isinstance(url, str):
            raise TypeError('url for .from_url must be a string')
        parsed = urlparse(url)
        new_kwargs = {}
        if parsed.netloc:
            host_part = parsed.netloc
        elif parsed.path and not parsed.netloc:
            # If you only pass the hostname (+ port possibly) without scheme or anything else
            host_part = parsed.path
        else:
            raise ValueError(f'Unsupported url specification: {url}')

        if ':' in host_part:
            hostname, port = host_part.rsplit(':', 1)
            port = int(port)
        else:
            hostname = host_part
            if parsed.scheme:
                port = cls.PROTOCOL_PORT_MAPPING[parsed.scheme]
            else:
                port = None
        new_kwargs['hostname'] = hostname
        if port is not None:
            new_kwargs['ui_port'] = port
        if parsed.scheme:
            new_kwargs['ui_protocol'] = parsed.scheme
        new_kwargs.update(kwargs)
        return cls(**new_kwargs)

    def new_rest_api_instance(
            self, entry_point=None, auth=None, logger="default", verify_ssl=False):
        """Returns new REST API instance."""
        return MiqApi(
            entry_point=entry_point or self.url_path('/api'),
            auth=auth or (conf.credentials["default"]["username"],
                          conf.credentials["default"]["password"]),
            logger=self.rest_logger if logger == "default" else logger,
            verify_ssl=verify_ssl)

    @cached_property
    def rest_api(self):
        return self.new_rest_api_instance()

    @cached_property
    def miqqe_version(self):
        """Returns version of applied JS patch or None if not present"""
        result = self.ssh_client.run_command(r'grep "[0-9]\\+" /var/www/miq/vmdb/.miqqe_version')
        if result.success:
            return int(result.output)
        return None

    @property
    def url(self):
        """Returns a proper URL of the appliance.

        If the ports do not correspond the protocols' default port numbers, then the ports are
        explicitly specified as well.
        """
        show_port = self.PROTOCOL_PORT_MAPPING[self.ui_protocol] != self.ui_port
        if show_port:
            return f'{self.ui_protocol}://{self.hostname}:{self.ui_port}/'
        else:
            return f'{self.ui_protocol}://{self.hostname}/'

    def url_path(self, path):
        """generates URL with an additional path. Useful for generating REST or SSUI URLs."""
        return '{}/{}'.format(self.url.rstrip('/'), path.lstrip('/'))

    @property
    def disks_and_partitions(self):
        """Returns list of all disks and partitions"""
        disks_and_partitions = self.ssh_client.run_command(
            "ls -1 /dev/ | egrep '^[sv]d[a-z][0-9]?'").output.strip()
        disks_and_partitions = re.split(r'\s+', disks_and_partitions)
        return sorted(f'/dev/{disk}' for disk in disks_and_partitions)

    @property
    def disks(self):
        """Returns list of disks only, excludes their partitions"""
        disk_regexp = re.compile('^/dev/[sv]d[a-z]$')
        return [
            disk for disk in self.disks_and_partitions
            if disk_regexp.match(disk)
        ]

    @property
    def unpartitioned_disks(self):
        """Returns list of any disks that have no partitions"""
        partition_regexp = re.compile('^/dev/[sv]d[a-z][0-9]$')
        unpartitioned_disks = set()

        for disk in self.disks:
            add = True
            for dp in self.disks_and_partitions:
                if dp.startswith(disk) and partition_regexp.match(dp) is not None:
                    add = False
            if add:
                unpartitioned_disks.add(disk)
        return sorted(disk for disk in unpartitioned_disks)

    @cached_property
    def product_name(self):
        try:
            return self.rest_api.product_info['name']
        except (AttributeError, KeyError, OSError, ConnectionError):
            self.log.info(
                'appliance.product_name could not be retrieved from REST, falling back')
            try:
                # TODO: Review this section. Does not work unconfigured
                # # We need to print to a file here because the deprecation warnings make it hard
                # # to get robust output and they do not seem to go to stderr
                # result = self.ssh_client.run_rails_command(
                #     '"File.open(\'/tmp/product_name.txt\', \'w\') '
                #     '{|f| f.write(I18n.t(\'product.name\')) }"')
                # result = self.ssh_client.run_command('cat /tmp/product_name.txt')
                # return result.output

                res = self.ssh_client.run_command('cat /etc/redhat-release')
                if res.failed:
                    raise RuntimeError('Unable to retrieve /etc/redhat-release')
                version_string = res.output.strip()
                if 'CentOS' in version_string:
                    return 'ManageIQ'
                else:
                    return 'CFME'
            except Exception:
                logger.exception(
                    "Couldn't fetch the product name from appliance, using ManageIQ as default")
                return 'ManageIQ'

    @cached_property
    def is_downstream(self):
        return self.product_name != 'ManageIQ'

    @property
    def version(self):
        return Version(self._version) if self._version else self._version_from_rest()

    def _version_from_rest(self):
        try:
            return Version(self.rest_api.server_info['version'])
        except (AttributeError, KeyError, OSError, APIException):
            self.log.exception('Exception fetching appliance version from REST, trying ssh')
            return self.ssh_client.vmdb_version

    def verify_version(self):
        """verifies if the actual appliance version matches the local stored one"""
        return self.version == self._version_from_rest()

    @cached_property
    def build(self):
        try:
            return self.rest_api.server_info['build']
        except (AttributeError, KeyError, OSError):
            self.log.exception('appliance.build could not be retrieved from REST, falling back')
            res = self.ssh_client.run_command('cat /var/www/miq/vmdb/BUILD')
            if res.failed:
                raise RuntimeError('Unable to retrieve appliance VMDB version')
            return res.output.strip("\n")

    @cached_property
    def os_version(self):
        # Currently parses the os version out of redhat release file to allow for
        # rhel and centos appliances
        res = self.ssh_client.run_command(
            r"cat /etc/redhat-release | sed 's/.* release \(.*\) (.*/\1/' #)")
        if res.failed:
            raise RuntimeError('Unable to retrieve appliance OS version')
        return Version(res.output)

    @cached_property
    def log(self):
        return create_sublogger(self.hostname)

    @cached_property
    def coverage(self):
        return ui_coverage.CoverageManager(self)

    def ssh_client_with_privatekey(self):
        with open(conf_path.join('appliance_private_key').strpath, 'w') as key:
            key.write(conf.credentials['ssh']['private_key'])
        connect_kwargs = {
            'hostname': self.hostname,
            'username': conf.credentials['ssh']['ssh-user'],
            'key_filename': conf_path.join('appliance_private_key').strpath,
        }
        ssh_client = ssh.SSHClient(**connect_kwargs)
        # FIXME: properly store ssh clients we made
        store.ssh_clients_to_close.append(ssh_client)
        return ssh_client

    @cached_property
    def ssh_client(self):
        """Creates an ssh client connected to this appliance

        Returns: A configured :py:class:``utils.ssh.SSHClient`` instance.

        Usage:

            with appliance.ssh_client as ssh:
                result = ssh.run_command('...')

        Note:

            The credentials default to those found under ``ssh`` key in ``credentials.yaml``.

        """
        logger.debug('Waiting for SSH to %s to become connective.',
                     self.hostname)
        self.wait_for_ssh()
        logger.debug('SSH port on %s ready.', self.hostname)

        # IPAppliance.ssh_client only connects to its address
        if self.openshift_creds:
            connect_kwargs = {
                'hostname': self.openshift_creds['hostname'],
                'username': self.openshift_creds['ssh']['username'],
                'password': self.openshift_creds['ssh']['password'],
                'oc_username': self.openshift_creds['username'],
                'oc_password': self.openshift_creds['password'],
                'container': self.container,
                'is_pod': self.is_pod,
                'port': self.ssh_port,
                'project': self.project
            }
        else:
            connect_kwargs = {
                'hostname': self.hostname,
                'username': conf.credentials['ssh']['username'],
                'password': conf.credentials['ssh']['password'],
                'container': self.container,
                'is_pod': self.is_pod,
                'port': self.ssh_port,
                'strict_host_key_checking': False,
            }
        connect_kwargs.update({'is_dev': self.is_dev})

        def create_ssh_connection():
            ssh_client = ssh.SSHClient(**connect_kwargs)
            try:
                ssh_client.get_transport().is_active()
                logger.info('default appliance ssh credentials are valid')
            except Exception as e:
                if self.is_dev:
                    raise Exception(f'SSH access on a dev appliance (unsupported): {e}')
                logger.exception(
                    ('default appliance ssh credentials failed: {}, '
                     'trying establish ssh connection using ssh private key').format(e))
                ssh_client.close()

                ssh_client = self.ssh_client_with_privatekey()
            assert ssh_client.run_command('true').success
            return ssh_client

        ssh_client = wait_for(func=create_ssh_connection, delay=5, timeout=120).out
        # FIXME: properly store ssh clients we made
        store.ssh_clients_to_close.append(ssh_client)
        return ssh_client

    @cached_property
    def default_iface(self):
        default_iface_cmd = self.ssh_client.run_command(
            "ip r | awk '/^default/ { print $5 }'")
        assert default_iface_cmd.success
        return default_iface_cmd.output.strip()

    @property
    def swap(self):
        """Retrieves the value of swap for the appliance. Might raise an exception if SSH fails.

        Return:
            An integer value of swap in the VM in megabytes. If ``None`` is returned, it means it
            was not possible to parse the command output.

        Raises:
            :py:class:`paramiko.ssh_exception.SSHException` or :py:class:`socket.error`
        """
        try:
            server = self.rest_api.get_entity_by_href(self.rest_api.server_info['server_href'])
            return server.system_swap_used / 1024 / 1024
        except (AttributeError, KeyError, OSError):
            self.log.exception('appliance.swap could not be retrieved from REST, falling back')
            value = self.ssh_client.run_command(
                'free -m | tr -s " " " " | cut -f 3 -d " " | tail -n 1', timeout=15)
            try:
                value = int(value.output.strip())
            except (TypeError, ValueError):
                value = None
            return value

    def event_listener(self):
        """Returns an instance of the event listening class pointed to this appliance."""
        from cfme.utils.events import RestEventListener
        return RestEventListener(self)

    def diagnose_evm_failure(self):
        """Go through various EVM processes, trying to figure out what fails

        Returns: A string describing the error, or None if no errors occurred.

        This is intended to be run after an appliance is configured but failed for some reason,
        such as in the template tester.

        """
        logger.info('Diagnosing EVM failures, this can take a while...')

        if not self.hostname:
            return 'appliance has no IP Address; provisioning failed or networking is broken'

        logger.info('Checking appliance SSH Connection')
        if not self.is_ssh_running:
            return 'SSH is not running on the appliance'

        # Now for the DB
        logger.info('Checking appliance database')
        if not self.db.online:
            # postgres isn't running, try to start it
            logger.info('Database is not online, restarting')
            try:
                self.db_service.restart()
            except SystemdException as ex:
                return f'postgres failed to start: \n{ex.message}'
            else:
                return 'postgres was not running for unknown reasons'

        if not self.db.has_database:
            return 'vmdb_production database does not exist'

        if not self.db.has_tables:
            return 'vmdb_production has no tables'

        # try to start EVM
        logger.info('Checking appliance evmserverd service')
        try:
            self.evmserverd.restart()
        except ApplianceException as ex:
            return 'evmserverd failed to start:\n{}'.format(ex.args[0])

        # This should be pretty comprehensive, but we might add some net_checks for
        # 3000, 4000, and 80 at this point, and waiting a reasonable amount of time
        # before exploding if any of them don't appear in time after evm restarts.

    @logger_wrap("Set NTP Sources: {}")
    def set_ntp_sources(self, log_callback=None):
        """Sets NTP sources for running appliance from cfme_data.clock_servers"""
        log_callback('Fixing appliance clock')
        client = self.ssh_client

        # checking whether chrony is installed
        check_cmd = 'yum list installed chrony'
        if client.run_command(check_cmd).failed:
            raise ApplianceException("Chrony isn't installed")

        # # checking whether it is enabled and enable it

        if not self.chronyd.enabled:
            logger.debug("chrony will start on system startup")
            self.chronyd.enable()
            self.chronyd.daemon_reload()

        # Retrieve time servers from yamls
        try:
            logger.debug('obtaining clock servers from config file')
            time_servers = conf.cfme_data.clock_servers
            assert time_servers
        except (KeyError, AttributeError, AssertionError):
            msg = 'No clock servers configured in cfme_data.yaml'
            log_callback(msg)
            raise ApplianceException(msg)

        logger.info('Setting NTP servers from config file: %s', time_servers)

        self.update_advanced_settings({'ntp': {'server': time_servers}})

        # check that chrony is running correctly now
        chrony_check = client.run_command('chronyc tracking')
        if not chrony_check.success:
            raise ApplianceException("chrony doesn't work. tracking output: {e}"
                                     .format(e=chrony_check.output))

    @property
    def is_miqqe_patch_candidate(self):
        return self.version < "5.6.3"

    @property
    def miqqe_patch_applied(self):
        return self.miqqe_version == current_miqqe_version

    @logger_wrap("Patch appliance with MiqQE js: {}")
    def patch_with_miqqe(self, log_callback=None):
        # (local_path, remote_path, md5/None) trio
        autofocus_patch = VersionPicker({
            '5.5': 'autofocus.js.diff',
            '5.7': 'autofocus_57.js.diff'
        }).pick(self.version)
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
        self.evmserverd.restart()
        logger.info("Waiting for Web UI to start")
        wait_for(
            func=self.is_web_ui_running,
            message='appliance.is_web_ui_running',
            delay=20,
            timeout=300)
        logger.info("Web UI is up and running")
        self.ssh_client.run_command(
            f"echo '{current_miqqe_version}' > /var/www/miq/vmdb/.miqqe_version")
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
        result = client.run_command("ls /opt/rh/cfme-gemset")
        if result.failed:
            return  # Not needed
        log_callback('Fixing Gemfile issue')
        # Check if the error is there
        result = client.run_rails_command("puts 1")
        if result.success:
            return  # All OK!
        client.run_command('echo "export BUNDLE_GEMFILE=/var/www/miq/vmdb/Gemfile" >> /etc/bashrc')
        # To be 100% sure
        self.reboot(wait_for_miq_ready=False, log_callback=log_callback)

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
        result = client.run_rake_command("assets:clobber")
        if result.failed:
            msg = f'Appliance {self.hostname} failed to nuke old assets'
            log_callback(msg)
            raise ApplianceException(msg)

        store.terminalreporter.write_line('Phase 2 of 2: rake assets:precompile')
        result = client.run_rake_command("assets:precompile")
        if result.failed:
            msg = f'Appliance {self.hostname} failed to precompile assets'
            log_callback(msg)
            raise ApplianceException(msg)

        store.terminalreporter.write_line('Asset precompilation done')
        return result.rc

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
        self.db.wait_for()

        # Make sure the working dir exists
        client.run_command(f'mkdir -p /tmp/{source}')

        export_opts = 'DOMAIN={} EXPORT_DIR=/tmp/{} PREVIEW=false OVERWRITE=true'.format(source,
            source)
        export_cmd = f'evm:automate:export {export_opts}'
        log_callback(f'Exporting domain ({export_cmd}) ...')
        result = client.run_rake_command(export_cmd)
        if result.failed:
            msg = f'Failed to export {source} domain'
            log_callback(msg)
            raise ApplianceException(msg)

        ro_fix_cmd = ("sed -i 's/system: true/system: false/g' "
                      "/tmp/{}/{}/__domain__.yaml".format(source, source))
        result = client.run_command(ro_fix_cmd)
        if result.failed:
            msg = f'Setting {dest} domain to read/write failed'
            log_callback(msg)
            raise ApplianceException(msg)

        import_opts = f'DOMAIN={source} IMPORT_DIR=/tmp/{source} PREVIEW=false'
        import_opts += f' OVERWRITE=true IMPORT_AS={dest} ENABLED=true'
        import_cmd = f'evm:automate:import {import_opts}'
        log_callback(f'Importing domain ({import_cmd}) ...')
        result = client.run_rake_command(import_cmd)
        if result.failed:
            msg = f'Failed to import {dest} domain'
            log_callback(msg)
            raise ApplianceException(msg)

        return result.rc, result.output

    def get_repofile_list(self):
        """Returns list of repofiles present at the appliance.

        Ignores certain files, like redhat.repo.
        """
        repofiles = self.ssh_client.run_command('ls /etc/yum.repos.d').output.strip().split('\n')
        return [f for f in repofiles if f not in {"redhat.repo"} and f.endswith(".repo")]

    def read_repos(self):
        """Reads repofiles so it gives you mapping of id and url."""
        repo_id_url_mapping = {}
        name_regexp = re.compile(r"^\[update-([^\]]+)\]")
        baseurl_regexp = re.compile(r"baseurl\s*=\s*([^\s]+)")
        for repofile in self.get_repofile_list():
            ssh_result = self.ssh_client.run_command(f"cat /etc/yum.repos.d/{repofile}")
            if ssh_result.failed:
                # Something happened meanwhile?
                continue
            out = ssh_result.output.strip()
            name_match = name_regexp.search(out)
            if name_match is None:
                continue
            baseurl_match = baseurl_regexp.search(out)
            if baseurl_match is None:
                continue
            repo_id_url_mapping[name_match.groups()[0]] = baseurl_match.groups()[0]
        return repo_id_url_mapping

    # Regexp that looks for product type and version in the update URL
    product_url_regexp = re.compile(
        r"/((?:[A-Z]+|CloudForms|rhel|RHEL_Guest))(?:-|/|/server/)(\d+[^/]*)/")

    def find_product_repos(self):
        """Returns a dictionary of products, where the keys are names of product (repos) and values
            are dictionaries where keys are the versions and values the names of the repositories.
        """
        products = {}
        for repo_name, repo_url in self.read_repos().items():
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
        filename = f"/etc/yum.repos.d/{repo_id}.repo"
        logger.info("Writing a new repofile %s %s", repo_id, repo_url)
        self.ssh_client.run_command(f'echo "[update-{repo_id}]" > {filename}')
        self.ssh_client.run_command(f'echo "name=update-url-{repo_id}" >> {filename}')
        self.ssh_client.run_command(f'echo "baseurl={repo_url}" >> {filename}')
        for k, v in kwargs.items():
            self.ssh_client.run_command(f'echo "{k}={v}" >> {filename}')
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
        for repo_id, url in self.read_repos().items():
            if url == repo_url:
                # It is already there, so just enable it
                self.enable_disable_repo(repo_id, True)
                return repo_id
        return self.write_repofile(fauxfactory.gen_alpha(), repo_url, **kwargs)

    def enable_disable_repo(self, repo_id, enable):
        logger.info("%s repository %s", "Enabling" if enable else "Disabling", repo_id)
        return self.ssh_client.run_command(
            "sed -i 's/^enabled=./enabled={}/' /etc/yum.repos.d/{}.repo".format(
                1 if enable else 0, repo_id)).success

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

        Kwargs:
            log_callback: logger to log against
            skip_broken (boolean): Pass --skip-broken to the yum update call. Defaults to False.
            reboot (boolean): Reboot the appliance after the upgrade. Defaults to True.
            streaming (boolean): Pass stream_output arg to SSHClient. Defaults to False.
            cleanup (boolean): Clean the /etc/yum.repos.d directory of all files except
            redhat.repo. Defaults to True.

        Returns:
            SSHResult object
        """
        urls = list(urls)
        log_callback = kwargs.pop("log_callback")
        skip_broken = kwargs.pop("skip_broken", False)
        reboot = kwargs.pop("reboot", True)
        streaming = kwargs.pop("streaming", False)
        cleanup = kwargs.pop('cleanup', True)
        log_callback('updating appliance')
        if not urls:
            basic_info = conf.cfme_data.get('basic_info', {})
            if os.environ.get('updates_urls'):
                # try to pull URLs from env if var is non-empty
                urls.extend(os.environ['update_urls'].split())
            else:
                # fall back to cfme_data
                updates_url = basic_info.get('rhel7_updates_url')

                if updates_url:
                    urls.append(updates_url)

        if streaming:
            client = self.ssh_client(stream_output=True)
        else:
            client = self.ssh_client

        if cleanup:
            logger.info("Cleaning the /etc/yum.repos.d directory")
            client.run_command(
                "cd /etc/yum.repos.d && find . -not -name 'redhat.repo' "
                "-not -name 'rhel-source.repo' -not -name . -exec rm {} \\;")

        for url in urls:
            self.add_product_repo(url)

        # update
        log_callback('Running rhel updates on appliance')
        # clean yum beforehand to clear metadata from earlier update repos, if any
        try:
            skip = '--skip-broken' if skip_broken else ''
            result = client.run_command(f'yum update -y --nogpgcheck {skip}',
                timeout=3600)
        except socket.timeout:
            msg = 'SSH timed out while updating appliance, exiting'
            log_callback(msg)
            # failure to update is fatal, kill this process
            raise KeyboardInterrupt(msg)

        self.log.error(result.output)
        if result.failed:
            self.log.error('appliance update failed')
            msg = f'Appliance {self.hostname} failed to update RHEL, error in logs'
            log_callback(msg)
            raise ApplianceException(msg)

        if reboot:
            self.reboot(wait_for_miq_ready=False, log_callback=log_callback)

        return result

    def upgrade(self, upgrade_to, cfme_only=True, reboot=False):
        """ Upgrade an appliance
        Args:
            upgrade_to (str): Stream for appliance upgrade. supported (5.9.z, 5.10.z, 5.11.z)
            cfme_only (bool): Update cfme packages only or all available updates.
            reboot (bool): Reboot appliance after upgrade.

        Note: Appliance always upgrades to latest available version.
        In supported stream `.z`indicate latest available.
        """

        logger.info("Appliance upgrade process started")

        if self.version.series() not in upgrade_to:
            # TODO: Add support of major upgrade
            raise NotImplementedError("Major upgrade not supported")

        supported_stream_repo_map = {
            "5.9.z": "update_url_59",
            "5.10.z": "update_url_510",
            "5.11.z": "update_url_511",
        }
        try:
            update_url = conf.cfme_data["basic_info"][supported_stream_repo_map[upgrade_to]]
        except (KeyError, IndexError):
            raise ValueError("Need to specify the correct upgrade path in cfme_data.yaml")

        logger.debug("Adding update repo to appliance")
        result = self.ssh_client.run_command(f"curl {update_url} -o /etc/yum.repos.d/update.repo")
        logger.debug(result.output)

        self.evmserverd.stop()

        logger.info("Running yum update")
        cmd = " cfme" if cfme_only else ""
        try:
            result = self.ssh_client.run_command(f"yum -y update{cmd}", timeout=3600)
        except socket.timeout:
            logger.error(f"SSH timed out while updating appliance: {result.output}")

        # clear cached properties for DB instances, in case of schema change during upgrade
        del self.db.__dict__['client']  # client DB instance caches tables/rows/columns
        del self.__dict__['db_service']  # service name might change, depends on self.db

        # May be chance to update kernel with all update.
        if reboot or not cfme_only:
            self.reboot()
        else:
            self.db_service.restart()
            self.evmserverd.start()

        self.wait_for_miq_ready()
        logger.info("Appliance upgrade completed")

    def utc_time(self):
        """Get UTC time of appliance"""
        if self.is_dev:
            logger.info('Using local UTC time on dev appliance')
            return datetime.now(pytz.UTC)
        client = self.ssh_client
        result = client.run_command('date --iso-8601=seconds -u')
        if result.success:
            return dateutil.parser.parse(result.output)
        else:
            raise Exception(f"Couldn't get datetime: {result.output}")

    def _check_appliance_ui_wait_fn(self):
        # Get the URL, don't verify ssl cert
        try:
            # If we don't request text/html, there is a short window during the
            # appliance HA DB failover when the evmserverd is not in OK state
            # but returns HTTP 200 while with requesting the text/html, we get
            # HTTP 500. Browsers are requesting the text/html, so we should.
            # probably as well.
            response = requests.get(self.url, timeout=15, verify=False,
                                    headers={'Accept': 'text/html'})
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

    @logger_wrap("Restart EVM Service: {}")
    def restart_evm_rude(self, log_callback=None):
        """Restarts the ``evmserverd`` service on this appliance"""
        store.terminalreporter.write_line('evmserverd is being restarted, be patient please')
        with self.ssh_client as ssh:
            self.evmserverd.stop()
            log_callback('Waiting for evm service to stop')
            try:
                wait_for(
                    lambda: self.evmserverd.running, num_sec=120, fail_condition=True, delay=5,
                    message='evm service to stop')
            except TimedOutError:
                # Don't care if it's still running
                pass
            log_callback('killing any remaining processes and restarting postgres')
            ssh.run_command('killall -9 ruby')
            self.db_service.restart()
            log_callback('Waiting for database to be available')
            wait_for(
                lambda: self.db.is_online, num_sec=90, delay=5,
                message="database to be available")
            self.evmserverd.start()

    @logger_wrap("Rebooting Appliance: {}")
    def reboot(self, wait_for_miq_ready=True, log_callback=None):
        log_callback('Rebooting appliance')
        client = self.ssh_client

        old_uptime = client.uptime()
        client.run_command('reboot')

        wait_for(lambda: client.uptime() < old_uptime, handle_exception=True,
            num_sec=600, message='appliance to reboot', delay=10)

        if wait_for_miq_ready:
            self.wait_for_miq_ready()

    @logger_wrap("Waiting for web_ui: {}")
    def wait_for_miq_ready(self, num_sec: int = 900, log_callback=None):
        """Waits for the web UI and API server to be ready / to not ready

        Args:
            num_secs: Number of seconds to wait until timeout (default ``900``)
            log_callback: Function to use for writing log messages.
        """
        (log_callback or self.log.info)('Waiting for web UI to appear')
        result, secs_taken = wait_for(self._check_appliance_ui_wait_fn,
                                      num_sec=num_sec, fail_condition=False, delay=10)
        self.wait_for_api_available(num_sec - secs_taken)
        return result

    def wait_for_api_available(self, num_sec=600):
        """ Waits for the MIQ API to be available. Invalidates the cached client.

        Args:
            num_sec: Number of seconds to wait until num_sec(default ``600``)
        """

        def _check_appliance_api_ready():
            try:
                # There are 2 hard problems in computer science: cache
                # invalidation, naming things, and off-by-1 errors.
                # -- Leon Bambrick
                #
                # Try invalidating stale cached api object if exists
                try:
                    del self.__dict__['rest_api']
                except KeyError:
                    pass
                api = self.rest_api

                # Make sure we really make a new request. Perhaps accessing the
                # rest_api property just creates a client object but no network
                # communicatin is done until we access some property of the
                # client.
                assert api.server_info['server_href']
                self.log.info("Appliance REST API ready")
                return api
            except APIException as exc:
                self.log.warning('Appliance RESTAPI not ready: %s', exc)
                return False

        api, _ = wait_for(func=_check_appliance_api_ready, num_sec=num_sec, delay=10)
        return api

    @logger_wrap("Install VDDK: {}")
    def install_vddk(self, force=False, vddk_url=None, log_callback=None):
        """Install the vddk on a appliance"""

        def log_raise(exception_class, message):
            log_callback(message)
            raise exception_class(message)

        if vddk_url is None:  # fallback to VDDK 5.5
            vddk_url = conf.cfme_data.get("basic_info", {}).get("vddk_url", {}).get("v5_5")
        if vddk_url is None:
            raise Exception("vddk_url not specified!")

        with self.ssh_client as client:
            is_already_installed = False
            if client.run_command('test -d /usr/lib/vmware-vix-disklib/lib64').success:
                is_already_installed = True

            if not is_already_installed or force:

                # start
                filename = vddk_url.split('/')[-1]

                # download
                log_callback('Downloading VDDK')
                result = client.run_command(f'curl {vddk_url} -o {filename}')
                if result.failed:
                    log_raise(Exception, "Could not download VDDK")

                # install
                log_callback('Installing vddk')
                result = client.run_command(
                    f'yum -y install {filename}')
                if result.failed:
                    log_raise(
                        Exception,
                        f'VDDK installation failure (rc: {result.rc})\n{result.output}'
                    )

                # verify
                log_callback('Verifying vddk')
                result = client.run_command('ldconfig -p | grep vix')
                if len(result.output) < 2:
                    log_raise(
                        Exception,
                        "Potential installation issue, libraries not detected\n{}"
                        .format(result.output)
                    )

    @logger_wrap("Uninstall VDDK: {}")
    def uninstall_vddk(self, log_callback=None):
        """Uninstall the vddk from an appliance"""
        with self.ssh_client as client:
            is_installed = client.run_command('test -d /usr/lib/vmware-vix-disklib/lib64').success
            if is_installed:
                result = client.run_command('yum -y remove vmware-vix-disklib')
                if result.failed:
                    log_callback('VDDK removing failure (rc: {})\n{}'
                                 .format(result.rc, result.output))
                    raise Exception('VDDK removing failure (rc: {})\n{}'
                                    .format(result.rc, result.output))
                else:
                    log_callback('VDDK has been successfully removed.')
            else:
                log_callback('VDDK is not installed.')

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
            log_callback(f'Downloading SDK from {sdk_url}')
            result = ssh.run_command(
                'wget {url} -O {file} > /root/unzip.out 2>&1'.format(
                    url=sdk_url, file=filename))
            if result.failed:
                log_raise(Exception, f'Could not download Netapp SDK: {result.output}')

            log_callback(f'Extracting SDK ({filename})')
            result = ssh.run_command(
                f'unzip -o -d /var/www/miq/vmdb/lib/ {filename}')
            if result.failed:
                log_raise(Exception, f'Could not extract Netapp SDK: {result.output}')

            path = f'/var/www/miq/vmdb/lib/{foldername}/lib/linux-64'
            # Check if we haven't already added this line
            if ssh.run_command(f"grep -F '{path}' /etc/default/evm").failed:
                log_callback(f'Installing SDK ({foldername})')
                result = ssh.run_command(
                    'echo "export LD_LIBRARY_PATH=\\$LD_LIBRARY_PATH:{}"'
                    '>> /etc/default/evm'.format(
                        path))
                if result.failed:
                    log_raise(Exception, 'SDK installation failure ($?={}): {}'
                              .format(result.rc, result.output))
            else:
                log_callback("Not needed to install, already done")

            log_callback('ldconfig')
            ssh.run_command('ldconfig')

            log_callback('Modifying YAML configuration')
            c_yaml = {'product': {'storage': True}}
            self.update_advanced_settings(c_yaml)

            # To mark that we installed netapp
            ssh.run_command("touch /var/www/miq/vmdb/HAS_NETAPP")

            if reboot:
                self.reboot(log_callback=log_callback)
            else:
                log_callback(
                    'Appliance must be restarted before the netapp functionality can be used.')
        clear_property_cache(self, 'is_storage_enabled')

    @logger_wrap('Updating appliance UUID: {}')
    def update_guid(self, log_callback=None):
        guid_gen = 'uuidgen |tee /var/www/miq/vmdb/GUID'
        log_callback(f'Running {guid_gen} to generate UUID')
        with self.ssh_client as ssh:
            result = ssh.run_command(guid_gen)
            assert result.success, 'Failed to generate UUID'
        log_callback('Updated UUID: {}'.format(str(result)))
        try:
            # There are 2 hard problems in computer science: cache
            # invalidation, naming things, and off-by-1 errors.
            # -- Leon Bambrick
            del self.__dict__['guid']  # invalidate cached_property
        except KeyError:
            logger.exception('Exception clearing cached_property "guid"')
        return str(result).rstrip('\n')  # should return UUID from stdout

    def wait_for_ssh(self, timeout=120):
        """Waits for appliance SSH connection to be ready

        Args:
            timeout: Number of seconds to wait until timeout (default ``600``)
        """
        wait_for(func=lambda: self.is_ssh_running,
                 message='appliance.is_ssh_running',
                 delay=1,
                 num_sec=timeout)

    @property
    def ansible_pod_name(self):
        if self.is_pod:
            get_ansible_name = ("basename $(oc get pods -lname=ansible "
                                "-o name --namespace={n})".format(n=self.project))
            return str(self.ssh_client.run_command(get_ansible_name, ensure_host=True)).strip()
        else:
            return None

    @property
    def is_ansible_pod_stopped(self):
        return self.ssh_client.run_command(
            "oc get pods|grep ansible", ensure_host=True
        ).failed

    @property
    def is_embedded_ansible_role_enabled(self):
        return self.server_roles.get("embedded_ansible", False)

    @property
    def is_embedded_ansible_running(self):
        supervisord = self.supervisord.running if self.version < '5.11' else True
        return self.is_embedded_ansible_role_enabled and supervisord

    def wait_for_embedded_ansible(self, timeout=None):
        """Waits for embedded ansible to be ready

        Args:
            timeout: Number of seconds to wait until timeout (default value is
            picked based on the appliance version or whether it is a pod)
        """
        if timeout is None:
            timeout = 2400 if self.version < '5.11' else 120
            if self.is_pod:
                # openshift's ansible pod gets ready very long first time.
                # it even gets restarted once or twice
                timeout *= 2

        wait_for(
            func=lambda: self.is_embedded_ansible_running,
            message='appliance.is_embedded_ansible_running',
            delay=60,
            num_sec=timeout
        )

    @cached_property
    def get_host_address(self):
        try:
            server = self.advanced_settings.get('server')
            if server:
                return server.get('host')
        except Exception as e:
            logger.exception(e)
            self.log.error('Exception occurred while fetching host address')

    def wait_for_host_address(self):
        try:
            wait_for(func=lambda: self.get_host_address,
                     fail_condition=None,
                     delay=5,
                     num_sec=120,
                     fail_func=lambda: delattr(self, 'get_host_address'))
            return self.get_host_address
        except Exception as e:
            logger.exception(e)
            self.log.error('waiting for host address from yaml_config timedout')

    @property
    def is_ssh_running(self):
        # WORKAROUND INC1296328
        # https://redhat.service-now.com/help?id=rh_ticket&table=incident&sys_id=65b98d19db701050c0c8464e139619eb
        is_pingable(self.hostname)

        if self.openshift_creds and 'hostname' in self.openshift_creds:
            hostname = self.openshift_creds['hostname']
        else:
            hostname = self.hostname
        return net_check(ports.SSH, hostname, force=True)

    @property
    def has_cli(self):
        return self.ssh_client.run_command('hash appliance_console_cli').success

    @property
    def is_idle(self):
        """Return appliance idle state measured by last production.log activity.
        It runs one liner script, which first gathers current date on appliance and then gathers
        date of last entry in production.log(which has to be parsed) with /api calls filtered
        (These calls occur every minute.)
        Then it deducts that last time in log from current date and if it is lower than idle_time it
        returns False else True.

        Args:

        Returns:
            True if appliance is idling for longer or equal to idle_time seconds.
            False if appliance is not idling for longer or equal to idle_time seconds.
        """
        idle_time = 3600
        ssh_output = self.ssh_client.run_command('if [ $((`date "+%s"` - `date -d "$(egrep -v '
            r'"(Processing by Api::ApiController\#index as JSON|Started GET "/api" for '
            '127.0.0.1|Completed 200 OK in)" /var/www/miq/vmdb/log/production.log | tail -1 |cut '
            '-d"[" -f3 | cut -d"]" -f1 | cut -d" " -f1)\" \"+%s\"`)) -lt {} ];'
            'then echo "False";'
            'else echo "True";'
            'fi;'.format(idle_time))
        return True if 'True' in ssh_output else False

    @cached_property
    def build_datetime(self):
        build_datetime_string = self.build.split('_', 1)[0]
        return datetime.strptime(build_datetime_string, '%Y%m%d%H%M%S')

    @cached_property
    def build_date(self):
        return self.build_datetime.date()

    def has_netapp(self):
        return self.ssh_client.appliance_has_netapp()

    @cached_property
    def guid(self):
        try:
            server = self.rest_api.get_entity_by_href(self.rest_api.server_info['server_href'])
            return server.guid
        except (AttributeError, KeyError, OSError):
            self.log.exception('appliance.guid could not be retrieved from REST, falling back')
            result = self.ssh_client.run_command('cat /var/www/miq/vmdb/GUID')
            return result.output

    @cached_property
    def evm_id(self):
        try:
            server = self.rest_api.get_entity_by_href(self.rest_api.server_info['server_href'])
            return server.id
        except (AttributeError, KeyError, OSError):
            self.log.exception('appliance.evm_id could not be retrieved from REST, falling back')
            miq_servers = self.db.client['miq_servers']
            return self.db.client.session.query(
                miq_servers.id).filter(miq_servers.guid == self.guid)[0][0]

    @property
    def fqdn(self):
        """fqdn from appliance_console
        This should likely be 'hostname' as that is what its called on the appliance
        Currently hostname attribute holds IP addr
        """
        return self.rest_api.get_entity_by_href(self.rest_api.server_info['server_href']).hostname

    def get_disabled_regions(self, provider=None):
        """Fetch appliance advanced config, get disabled regions for given provider's type

        Only relevant for cloud providers azure and ec2 at the moment

        Args:
            provider: A BaseProvider object with settings_key attribute

        Returns:
            Default: Dict of ems_<provider> keys and values of disabled_regions map
            when provider given: disabled_regions list from config
            when no matching config found: None
        """
        ems_config = self.advanced_settings.get('ems')
        if provider and ems_config:
            try:
                prov_config = ems_config.get(getattr(provider, 'settings_key', None), {})  # safe
                regions = prov_config['disabled_regions']  # KeyError
            except KeyError:
                regions = []
        elif ems_config:
            regions = {ems_key: yaml['disabled_regions']
                       for ems_key, yaml in ems_config.items()
                       if 'disabled_regions' in yaml}
        else:
            # 'ems' was NOT in advanced_settings
            regions = {}

        return regions

    def set_disabled_regions(self, provider, *regions):
        """Modify config to set disabled regions to given regions for the given provider's type

        Only relevant for cloud providers azure and ec2 at the moment

        Does NOT APPEND to the list of disabled regions, SETS it

        Args:
            provider: A BaseProvider object with settings_key attribute
            *regions: none, one or many region names, on None enables all regions for provider type

        Raises:
            AssertionError - when the disabled regions don't match after setting
            ApplianceException - when there's a KeyError modifying the yaml
        """
        try:
            yaml_conf = {
                'ems': {getattr(provider, 'settings_key', None): {'disabled_regions': regions}}
            }
        except KeyError:
            # catches not-found settings_key or 'None' when the provider doesn't have it
            raise ApplianceException('Provider %s settings_key attribute not set '
                                     'or not found in config %s'
                                     .format(provider, yaml_conf['ems']))

        self.update_advanced_settings(yaml_conf)
        assert self.get_disabled_regions(provider) == list(regions)  # its a tuple if empty

    @property
    def server_roles(self):
        """Return a dictionary of server roles from database"""
        asr = self.db.client['assigned_server_roles']
        sr = self.db.client['server_roles']
        all_role_names = {row[0] for row in self.db.client.session.query(sr.name)}
        # Query all active server roles assigned to this server
        query = self.db.client.session\
            .query(sr.name)\
            .join(asr, asr.server_role_id == sr.id)\
            .filter(asr.miq_server_id == self.evm_id)\
            .filter(asr.active == True)  # noqa
        active_roles = {row[0] for row in query}
        roles = {role_name: role_name in active_roles for role_name in all_role_names}
        dead_keys = ['database_owner', 'vdi_inventory']
        for key in roles:
            if not self.is_storage_enabled:
                if key.startswith('storage'):
                    dead_keys.append(key)
                if key == 'vmdb_storage_bridge':
                    dead_keys.append(key)
        for key in dead_keys:
            try:
                del roles[key]
            except KeyError:
                pass
        return roles

    @server_roles.setter
    def server_roles(self, roles):
        """Sets the server roles. Requires a dictionary full of the role keys with bool values."""
        if self.server_roles == roles:
            self.log.debug(' Roles already match, returning...')
            return
        ansible_old = self.server_roles.get('embedded_ansible', False)
        ansible_new = roles.get('embedded_ansible', False)
        enabling_ansible = ansible_old is False and ansible_new is True

        server_data = self.advanced_settings.get('server', {})
        server_data['role'] = ','.join([role for role, boolean in roles.items() if boolean])
        self.update_advanced_settings({'server': server_data})
        timeout = 600 if enabling_ansible else 300
        wait_for(lambda: self.server_roles == roles, num_sec=timeout, delay=15)
        if enabling_ansible:
            self.wait_for_embedded_ansible()

    def enable_embedded_ansible_role(self):
        """Enables embbeded ansible role

        This is necessary because server_roles does not wait long enough"""

        roles = self.server_roles
        roles['embedded_ansible'] = True
        try:
            self.server_roles = roles
        except TimedOutError:
            wait_for(lambda: self.server_roles == roles, num_sec=600, delay=15)
        self.wait_for_embedded_ansible()

    def disable_embedded_ansible_role(self):
        """disables embbeded ansible role"""

        roles = self.server_roles
        roles['embedded_ansible'] = False
        self.server_roles = roles

    def update_server_roles(self, changed_roles):
        server_roles = self.server_roles.copy()
        server_roles.update(changed_roles)
        self.server_roles = server_roles
        return server_roles == self.server_roles

    def wait_for_server_roles(self, server_roles, **kwargs):
        """Waits for the server roles to be set

        Warning: This may take awhile if it is a long list.

         Args:
            server_roles: list of server roles to be checked
         Returns:
            :py:class:`bool`
         """

        try:
            wait_for(lambda: all([self.server_roles[role] for role in server_roles]), **kwargs)
        except TimedOutError:
            return False
        else:
            return True

    def server_id(self):
        try:
            return self.server.sid
        except IndexError:
            return None

    def server_region_string(self):
        r = self.server.zone.region.number
        return "{} Region: Region {} [{}]".format(
            self.product_name, r, r)

    def region(self):
        return f"Region {self.server.zone.region.number}"

    def rename(self, new_name):
        """Changes appliance name

        Args:
            new_name: Name to set

        Note:
            Database must be up and running and evm service must be (re)started afterwards
            for the name change to take effect.
        """
        vmdb_config = {'server': {'name': new_name}}
        self.update_advanced_settings(vmdb_config)

    @cached_property
    def company_name(self):
        return self.advanced_settings["server"]["company"]

    def host_id(self, hostname):
        hosts = list(
            self.db.client.session.query(self.db.client["hosts"]).filter(
                self.db.client["hosts"].name == hostname
            )
        )
        if hosts:
            return str(hosts[0].id)
        else:
            return None

    @cached_property
    def is_storage_enabled(self):
        return 'storage' in self.advanced_settings.get('product', {})

    @property
    def advanced_settings(self):
        """Get settings from the base api/settings endpoint for appliance"""

        return self.rest_api.get(self.rest_api.collections.settings._href)

    def update_advanced_settings(self, settings_dict):
        """PATCH settings from the master server's api/server/:id/settings endpoint

        Will automatically update existing settings dictionary with settings_dict

        Args:
            data_dict: dictionary of the changes to be made to the yaml configuration
                       JSON dumps data_dict to pass as raw hash data to rest_api session
        Raises:
            ApplianceException when server_id isn't set
        """
        # Can only modify through server ID, raise if that's not set yet
        if self.server_id() is None:
            raise ApplianceException('No server id is set, cannot modify yaml config via REST')
        self.server.update_advanced_settings(settings_dict)

    def set_proxy(self, host, port, user=None, password=None, prov_type=None):
        vmdb_config = self.advanced_settings
        proxy_type = prov_type or 'default'
        settings = {'host': host,
                    'port': port,
                    'user': user,
                    'password': password}
        try:
            vmdb_config['http_proxy'][proxy_type] = settings
        except KeyError as ex:
            logger.error('Incorrect provider type')
            logger.exception(ex)
            raise ApplianceException('Impossible to create proxy with current provider type')
        self.update_advanced_settings(vmdb_config)

    def reset_proxy(self, prov_type=None):
        vmdb_config = self.advanced_settings
        proxy_type = prov_type or 'default'
        vmdb_config['http_proxy'][proxy_type] = False if self.version < "5.10" else "<<reset>>"
        self.update_advanced_settings(vmdb_config)

    def set_session_timeout(self, timeout=86400, quiet=True):
        """Sets the timeout of UI timeout.

        Args:
            timeout: Timeout in seconds
            quiet: Whether to ignore any errors
        """
        try:
            session_config = self.advanced_settings.get('session', {})
            if session_config.get('timeout') != timeout:
                session_config['timeout'] = timeout
                self.update_advanced_settings({'session': session_config})
        except Exception as ex:
            logger.error('Setting session timeout failed:')
            logger.exception(ex)
            if not quiet:
                raise

    def delete_all_providers(self):
        logger.info('Destroying all appliance providers')
        for prov in self.rest_api.collections.providers:
            prov.action.delete()

    def reset_automate_model(self):
        with self.ssh_client as ssh_client:
            ssh_client.run_rake_command("evm:automate:reset")

    def clean_appliance(self):
        starttime = time()
        self.evmserverd.stop()
        self.ssh_client.run_command('sync; '
                                    'sync; '
                                    'echo 3 > /proc/sys/vm/drop_caches')
        self.collectd.stop()
        self.db_service.restart()
        self.ssh_client.run_command('cd /var/www/miq/vmdb; '
                                    'bin/rake evm:db:reset')
        self.ssh_client.run_rake_command('db:seed')
        self.collectd.start()
        self.ssh_client.run_command('rm -rf /var/www/miq/vmdb/log/*.log*')
        self.ssh_client.run_command('rm -rf /var/www/miq/vmdb/log/apache/*.log*')
        self.evmserverd.start()
        self.evmserverd.wait_for_running()
        logger.debug('Cleaned appliance in: {}'.format(round(time() - starttime, 2)))

    def set_full_refresh_threshold(self, threshold=100):
        yaml_data = {'ems_refresh': {'full_refresh_threshold': threshold}}
        self.update_advanced_settings(yaml_data)

    def set_cap_and_util_all_via_rails(self):
        """Turns on Collect for All Clusters and Collect for all Datastores without using Web UI."""
        command = (
            'Metric::Targets.perf_capture_always = {:storage=>true, :host_and_cluster=>true};')
        self.ssh_client.run_rails_console(command, timeout=None)

    def set_cfme_server_relationship(self, vm_name, server_id=1):
        """Set MiqServer record to the id of a VM by name, effectively setting the CFME Server
        Relationship without using the Web UI."""
        command = ('miq_server = MiqServer.find_by(id: {});'
                   'miq_server.vm_id = Vm.find_by(name: \'{}\').id;'
                   'miq_server.save'.format(server_id, vm_name))
        self.ssh_client.run_rails_console(command, timeout=None)

    def set_pglogical_replication(self, replication_type=':none'):
        """Set pglogical replication type (:none, :remote, :global) without using the Web UI."""
        command = (f'MiqRegion.replication_type = {replication_type}')
        self.ssh_client.run_rails_console(command, timeout=None)

    def add_pglogical_replication_subscription(self, host):
        """Add a pglogical replication subscription without using the Web UI."""
        user = conf.credentials['ssh']['username']
        password = conf.credentials['ssh']['password']
        dbname = 'vmdb_production'
        port = 5432
        command = ('sub = PglogicalSubscription.new;'
                   'sub.dbname = \'{}\';'
                   'sub.host = \'{}\';'
                   'sub.user = \'{}\';'
                   'sub.password = \'{}\';'
                   'sub.port = {};'
                   'sub.save'.format(dbname, host, user, password, port))
        self.ssh_client.run_rails_console(command, timeout=None)

    def set_rubyrep_replication(self, host, port=5432, database='vmdb_production',
                                username='root', password=None):
        """Sets up rubyrep replication via advanced configuration settings yaml."""
        password = password or self._encrypt_string(conf.credentials['ssh']['password'])
        yaml_data = {'workers': {'worker_base': {'replication_worker': {'replication': {
            'destination': {}}}}}
        }
        dest = yaml_data['workers']['worker_base']['replication_worker']['replication'][
            'destination']
        dest['database'] = database
        dest['username'] = username
        dest['password'] = password
        dest['port'] = port
        dest['host'] = host
        logger.debug(f'Dest: {yaml_data}')
        self.update_advanced_settings(yaml_data)

    def wait_for_miq_server_workers_started(self, evm_tail=None, poll_interval=5):
        """Waits for the CFME's workers to be started by tailing evm.log for:
        'INFO -- : MIQ(MiqServer#wait_for_started_workers) All workers have been started'
        """
        if evm_tail is None:
            logger.info('Opening /var/www/miq/vmdb/log/evm.log for tail')
            evm_tail = SSHTail('/var/www/miq/vmdb/log/evm.log')
            evm_tail.set_initial_file_end()

        attempts = 0
        detected = False
        max_attempts = 60
        while (not detected and attempts < max_attempts):
            logger.debug(f'Attempting to detect MIQ Server workers started: {attempts}')
            for line in evm_tail:
                if 'MiqServer#wait_for_started_workers' in line:
                    if ('All workers have been started' in line):
                        logger.info('Detected MIQ Server is ready.')
                        detected = True
                        break
            sleep(poll_interval)  # Allow more log lines to accumulate
            attempts += 1
        if not (attempts < max_attempts):
            logger.error('Could not detect MIQ Server workers started in {}s.'.format(
                poll_interval * max_attempts))
        evm_tail.close()

    @logger_wrap("Setting dev branch: {}")
    def use_dev_branch(self, repo, branch, log_callback=None):
        """Sets up an exitsing appliance to change the branch to specified one and reset it.

        Args:
            repo: URL to the repo
            branch: Branch of that repo
        """
        with self.ssh_client as ssh_client:
            dev_branch_cmd = f'cd /var/www/miq/vmdb; git remote add dev_branch {repo}'
            if not ssh_client.run_command(dev_branch_cmd):
                ssh_client.run_command('cd /var/www/miq/vmdb; git remote remove dev_branch')
                if not ssh_client.run_command(dev_branch_cmd):
                    raise Exception('Could not add the dev_branch remote')
            # We now have the repo and now let's update it
            ssh_client.run_command('cd /var/www/miq/vmdb; git remote update')
            self.evmserverd.stop()
            ssh_client.run_command(
                f'cd /var/www/miq/vmdb; git checkout dev_branch/{branch}')
            ssh_client.run_command('cd /var/www/miq/vmdb; bin/update')
            self.evmserverd.start()
            self.evmserverd.wait_for_running()
            self.wait_for_miq_ready()

    def check_domain_enabled(self, domain):
        namespaces = self.db.client["miq_ae_namespaces"]
        q = self.db.client.session.query(namespaces).filter(
            namespaces.parent_id == None, namespaces.name == domain)  # NOQA (for is/==)
        try:
            return list(q)[0].enabled
        except IndexError:
            raise KeyError(f"No such Domain: {domain}")

    @logger_wrap('Configuring openldap external auth provider')
    def configure_openldap(self, auth_provider, log_callback=None):
        """This method changes the /etc/sssd/sssd.conf and /etc/openldap/ldap.conf files to set
            up the appliance for an external authentication with OpenLdap.
            Apache file configurations are updated, for webui to take effect.
            Args:
                auth_provider: auth provider object derived from cfme.utils.auth.MIQAuthProvider
        """
        # write /etc/hosts entry for ldap hostname  TODO DNS
        for key in ['ipaddress', 'cert_filename', 'cert_filepath', 'ldap_conf', 'sssd_conf']:
            if not auth_provider.get(key):  # either not set, or None
                raise ValueError('Auth Provider object {} needs attribute {} for external openldap'
                                 .format(auth_provider, key))

        self.ssh_client.run_command('echo "{}  {}" >> /etc/hosts'
                                    .format(auth_provider.ipaddress, auth_provider.host1))
        # place cert from local conf directory on ldap server
        self.ssh_client.put_file(local_file=conf_path.join(auth_provider.cert_filename).strpath,
                                 remote_file=auth_provider.cert_filepath)
        # configure ldap and sssd with conf file content from yaml
        assert self.ssh_client.run_command('echo "{s}" > {c}'
                                           .format(s=auth_provider.ldap_conf,
                                                   c=self.CONF_FILES['openldap']))
        assert self.ssh_client.run_command('echo "{s}" > {c}'
                                           .format(s=auth_provider.sssd_conf,
                                                   c=self.CONF_FILES['sssd']))
        assert self.ssh_client.run_command('chown -R root:root {}').format(self.CONF_FILES['sssd'])
        assert self.ssh_client.run_command('chmod 600 {}').format(self.CONF_FILES['sssd'])
        # copy miq/cfme template files for httpd ext auth config
        template_dir = self.CONF_FILES.get('downstream_templates'
                                           if self.is_downstream
                                           else 'upstream_templates')
        # pam httpd-auth and httpd remote-user.conf
        for conf_file in [self.CONF_FILES['pam_httpd_auth'], self.CONF_FILES['httpd_remote_user']]:
            assert self.ssh_client.run_command('cp {t}{c} {c}'.format(t=template_dir, c=conf_file))

        # https external-auth conf, template has extra '.erb' suffix
        assert self.ssh_client.run_command('cp {t}{c}.erb {c}'
                                           .format(t=template_dir,
                                                   c=self.CONF_FILES['httpd_ext_auth']))
        assert self.ssh_client.run_command('setenforce 0')
        self.sssd.restart()
        self.httpd.restart()
        self.wait_for_miq_ready()

        # UI configuration of auth provider type
        self.server.authentication.configure(auth_mode='external', auth_provider=auth_provider)

    @logger_wrap('Disabling openldap external auth provider')
    def disable_openldap(self, log_callback=None):
        self.server.authentication.configure_auth()
        files_to_remove = [
            self.CONF_FILES['sssd'],
            self.CONF_FILES['pam_httpd_auth'],
            self.CONF_FILES['httpd_ext_auth'],
            self.CONF_FILES['httpd_remote_user']
        ]
        for conf_file in files_to_remove:
            assert self.ssh_client.run_command(f'rm -f $(ls {conf_file})')
        self.evmserverd.restart()
        self.httpd.restart()
        self.wait_for_miq_ready()
        self.server.authentication.configure_auth(auth_mode='database')

    @logger_wrap('Configuring freeipa external auth provider')
    def configure_freeipa(self, auth_provider, log_callback=None):
        """Configure appliance UI and backend for freeIPA

        Args:
            auth_provider: An auth provider class derived from cfme.utils.auth.BaseAuthProvider
        Notes:
            Completes backend config via appliance_console_cli
            Completes UI configuration for external auth mode
        """
        if self.is_pod:
            # appliance_console_cli fails when calls hostnamectl --host. it seems docker issue
            # raise BZ ?
            assert str(self.ssh_client.run_command('hostname')).rstrip() == self.fqdn

        # First, clear any existing ipa config, runs clean if not configured
        self.appliance_console_cli.uninstall_ipa_client()
        self.wait_for_miq_ready()  # httpd restart in uninstall-ipa

        # ext auth ipa requires NTP sync
        if auth_provider.host1 not in self.server.settings.ntp_servers_values:
            self.server.settings.update_ntp_servers({'ntp_server_1': auth_provider.host1})

        # the evmserverd restart is necessary for the NTP sync to properly go through
        # in the subsequent command (appliance console IPA configuration)
        self.evmserverd.restart()
        self.wait_for_miq_ready()
        # since the browser will be stuck on the server settings page, and logout on next click
        # after the evmserverd restart, quit the browser before the next step.
        self.browser.quit_browser()

        # backend appliance configuration of ext auth provider
        self.appliance_console_cli.configure_ipa(**auth_provider.as_external_value())

        # UI configuration of auth provider type
        self.server.authentication.configure(auth_mode='external', auth_provider=auth_provider)

        # restart httpd
        self.httpd.restart()

    @logger_wrap('Disabling freeipa external auth provider')
    def disable_freeipa(self, log_callback=None):
        """Switch UI back to database authentication, and run --uninstall-ipa on appliance"""
        self.appliance_console_cli.uninstall_ipa_client()
        self.server.authentication.configure(auth_mode='database')
        # reset ntp servers
        self.server.settings.update_ntp_servers({'ntp_server_1': 'clock.corp.redhat.com'})
        self.wait_for_miq_ready()  # httpd restart in uninstall-ipa

    @logger_wrap('Configuring SAML external auth provider')
    def configure_saml(self, auth_provider, log_callback=None):
        """This method configures an appliance for external authentication with a SAML provider

            Apache file configurations are updated, waits for webui to take effect.
            Args:
                auth_provider: auth provider object derived from cfme.utils.auth.MIQAuthProvider
        """
        # appliance constants
        TEMPLATE_DIR = "/opt/rh/cfme-appliance/TEMPLATE"
        HTTP_DIR = "/etc/httpd/conf.d"
        SAML_DIR = "/etc/httpd/saml2"
        USER_CONF = "manageiq-remote-user.conf"
        EXT_CONF = "manageiq-external-auth-saml.conf"
        URL = f"https://{self.get_resolvable_hostname()}"

        # saml constants
        SAML_ENDPOINT = auth_provider.saml_endpoint
        TESTING_REALM = auth_provider.realms.get("testing")

        def _create_client(cert_string):
            """ Create the client on the SAML server"""
            keycloak_admin = auth_provider.get_keycloak_api(
                realm_name=TESTING_REALM
            )
            # create the payload object
            payload = dict(
                clientId=URL,
                adminUrl=f"{URL}/saml2",
                baseUrl=URL,
                protocol="saml",
                redirectUris=[f"{URL}/saml2/postResponse", f"{URL}/saml2/paosResponse"],
                defaultClientScopes=auth_provider.data.get("defaultClientScopes"),
                attributes={
                    "saml.encrypt": "true",
                    "saml.assertion.signature": "true",
                    "saml.server.signature": "true",
                    "saml.signing.certificate": cert_string,
                    "saml.encryption.certificate": cert_string,
                    "saml_assertion_consumer_url_redirect": f"{URL}/saml2/postResponse",
                    "saml_assertion_consumer_url_post": f"{URL}/saml2/postResponse",
                    "saml_single_logout_service_url_redirect": f"{URL}/saml2/logout"
                }
            )
            # send the payload
            keycloak_admin.create_client(payload)

        # 1) copy over template conf
        self.ssh_client.run_command("mkdir -p /etc/httpd/saml2")
        self.ssh_client.run_command(f"cp {TEMPLATE_DIR}/{HTTP_DIR}/{USER_CONF} {HTTP_DIR}/")
        self.ssh_client.run_command(f"cp {TEMPLATE_DIR}/{HTTP_DIR}/{EXT_CONF} {HTTP_DIR}/")
        # 2) Generate service provider files
        self.ssh_client.run_command(
            f"cd {SAML_DIR} && /usr/libexec/mod_auth_mellon/mellon_create_metadata.sh "
            f"{URL} {URL}/saml2"
        )
        # 3) Rename service provider files
        self.ssh_client.run_command(f"cd {SAML_DIR} && mv *.cert miqsp-cert.cert")
        self.ssh_client.run_command(f"cd {SAML_DIR} && mv *.key miqsp-key.key")
        self.ssh_client.run_command(f"cd {SAML_DIR} && mv *.xml miqsp-metadata.xml")

        # 4) create client on the SAML server
        cert_string = self.ssh_client.run_command(f"cat {SAML_DIR}/miqsp-cert.cert").output

        def _clean_cert_string(cert_string):
            """ get rid of unwanted -----BEGIN CERTIFICATE -------
            """
            cert_list = [l for l in cert_string.split("\n") if not l.startswith("----")]
            return "".join(cert_list)

        _create_client(_clean_cert_string(cert_string))

        # 5) Obtain identity provider's idp-metadata.xml file
        self.ssh_client.run_command(
            f"cd {SAML_DIR} && "
            f"curl -s -o idp-metadata.xml "
            f"{SAML_ENDPOINT}/realms/{TESTING_REALM}/protocol/saml/descriptor"
        )
        # 6) Restart httpd
        self.httpd.restart()
        self.wait_for_miq_ready()
        # 7) UI configuration of auth provider type
        self.server.authentication.configure(auth_mode='external', auth_provider=auth_provider)

    @logger_wrap('Disabling saml external auth provider')
    def disable_saml(self, auth_provider, log_callback=None):
        """Switch UI back to database authentication, remove necessary files and delete client
            from saml server
        """
        # appliance constants
        HTTP_DIR = "/etc/httpd/conf.d"
        SAML_DIR = "/etc/httpd/saml2"
        USER_CONF = "manageiq-remote-user.conf"
        EXT_CONF = "manageiq-external-auth-saml.conf"
        URL = f"https://{self.ssh_client.run_command('hostname').output.strip()}"

        # saml constants
        TESTING_REALM = auth_provider.realms.get("testing")

        def _delete_client():
            keycloak_admin = auth_provider.get_keycloak_api(
                realm_name=TESTING_REALM
            )
            # delete the client whose name corresponds to the appliance URL
            keycloak_admin.delete_client(keycloak_admin.get_client_id(URL))

        # 1) Delete the saml2 directory
        self.ssh_client.run_command(f"rm -rf {SAML_DIR}")
        # 2) Delete USER_CONF and EXT_CONF
        self.ssh_client.run_command(f"rm -f {HTTP_DIR}/{USER_CONF}")
        self.ssh_client.run_command(f"rm -f {HTTP_DIR}/{EXT_CONF}")
        # 3) Delete the client from the SAML server
        _delete_client()
        # 4) restart httpd
        self.httpd.restart()
        self.wait_for_miq_ready()
        # 5) change back to database auth_mode
        self.server.authentication.configure(auth_mode='database')

    @logger_wrap("Configuring VM Console: {}")
    def configure_vm_console_cert(self, log_callback=None):
        """This method generates a self signed SSL cert and installs it
           in the miq/vmdb/certs dir.   This cert will be used by the
           HTML 5 VM Console feature.  Note evmserverd needs to be restarted
           after running this.
        """
        log_callback('Installing SSL certificate')

        cert = conf.cfme_data['vm_console'].get('cert')
        if cert is None:
            raise Exception('vm_console:cert does not exist in cfme_data.yaml')

        # 5.11 and upstream need pyopenssl for this certificate generation
        # TODO convert the script to py3, use pip3 to install needed packages
        if not self.is_downstream or self.version >= '5.11':
            self.ssh_client.run_command('pip install pyopenssl')

        cert_file = os.path.join(cert.install_dir, 'server.cer')
        key_file = os.path.join(cert.install_dir, 'server.cer.key')
        cert_generator = scripts_path.join('gen_ssl_cert.py').strpath
        remote_cert_generator = os.path.join('/usr/bin', 'gen_ssl_cert.py')

        # Copy self signed SSL certificate generator to the appliance
        # because it needs to get the FQDN for the cert it generates.
        self.ssh_client.put_file(cert_generator, remote_cert_generator)

        # Generate cert
        command = (
            '{cert_generator}'
            ' --C "{country}"'
            ' --ST "{state}"'
            ' --L "{city}"'
            ' --O "{organization}"'
            ' --OU "{organizational_unit}"'
            ' --keyFile "{key}"'
            ' --certFile "{cert}"'
            .format(
                cert_generator=remote_cert_generator,
                country=cert.country,
                state=cert.state,
                city=cert.city,
                organization=cert.organization,
                organizational_unit=cert.organizational_unit,
                key=key_file,
                cert=cert_file,
            )
        )
        result = self.ssh_client.run_command(command)
        if not result == 0:
            raise Exception(
                'Failed to generate self-signed SSL cert on appliance: {}'.format(
                    result.output
                )
            )

    @logger_wrap('Get the resolvable hostname')
    def get_resolvable_hostname(self, log_callback=None):
        """Lookup the hostname based on self.hostname"""
        # Example lookups with self.hostname as IP and self.hostname as resolvable name
        # [root@host-192-168-55-85 ~]# host 1.2.3.137
        # 137.3.2.1.in-addr.arpa domain name pointer 137.test.miq.com.
        # [root@host-192-168-55-85 ~]# host 137.test.miq.com
        # 137.test.miq.com has address 1.2.3.137
        host_check = self.ssh_client.run_command(f'host {self.hostname}', ensure_host=True)
        log_callback(f'Parsing for resolvable hostname from "{host_check.output}"')
        fqdn = None  # just in case the logic gets weird
        if host_check.success and 'domain name pointer' in host_check.output:
            # resolvable and reverse lookup
            # parse out the resolved hostname
            fqdn = host_check.output.split(' ')[-1].rstrip('\n').rstrip('.')
            log_callback(f'Found FQDN by appliance IP: "{fqdn}"')
        elif host_check.success and 'has address' in host_check.output:
            # resolvable and address returned
            fqdn = self.hostname
            log_callback(f'appliance hostname attr is FQDN: "{fqdn}"')
        else:
            logger.warning('Bad RC from host command or unexpected output,'
                           ' no resolvable hostname found')
        return fqdn

    @logger_wrap('Configuring resolvable hostname')
    def set_resolvable_hostname(self, log_callback=None):
        """Try to lookup the hostname based on self.hostname, which is generally an IP

        Intended use is for appliances hosted on openstack, which will likely not have a FQDN
        hostname after deploying the image. Can be called against any appliance type.

        If a hostname is resolved for the IP, its used to set the hostname via appliance_cli
        If an IP is resolved for self.hostname, no action is taken
        If nothing is resolved, no action is taken

        Returns:
            Boolean, True if hostname was set
        """
        fqdn = self.get_resolvable_hostname()
        if fqdn is not None:
            log_callback(f'Setting FQDN "{fqdn}" via appliance_console_cli')
            result = self.appliance_console_cli.set_hostname(str(fqdn))
            return result.success
        else:
            logger.error('Unable to set resolvable hostname')
            return False

    def remove_resolvable_hostname(self):
        """remove a resolvable hostname from /etc/hosts directly
        USE WITH CAUTION as it mangles /etc/hosts,
        recommended only for seal_for_templatizing with sprout appliances
        """
        hosts_grep_cmd = f'grep {self.get_resolvable_hostname()} /etc/hosts'
        with self.ssh_client as ssh_client:
            if ssh_client.run_command(hosts_grep_cmd, ensure_host=True).success:
                # remove resolvable hostname from /etc/hosts
                # tuples of (loopback, replacement string) for each proto
                v6 = ('::1', re.escape('::1'.ljust(16)))
                v4 = ('127.0.0.1', re.escape('127.0.0.1'.ljust(16)))
                resolve_esc = re.escape(self.get_resolvable_hostname())
                for addr, fill in [v6, v4]:
                    # regex finds lines for loopback addrs where resolvable hostname set
                    # sed replaces with the ljust (space padded) loopback addr
                    ssh_client.run_command(
                        r"sed -i -r -e 's|({}\s..*){}|{}|' /etc/hosts"
                        .format(addr, resolve_esc, fill),
                        ensure_host=True
                    )

    def provider_based_collection(self, provider, coll_type='vms'):
        """Given a provider, fetches a collection for the given collection type

        Some collections are provider based, like infra vms and cloud instances
        This provides an easy way to pick which one is right for your provider

        Args:
            provider: provider class/instance for lookup
            coll_type: which collection type to return based on the provider type

        Notes:
            Add coll_type support as there are collections dependent on a provider type

        Examples:
            # returns the infra_vms collection
            appliance.collections.provider_based_collection(rhevm_provider, 'vms')
        """
        from cfme.cloud.provider import CloudProvider  # for checking provider type
        if coll_type == 'vms':
            return getattr(self.collections,
                           'cloud_instances' if provider.one_of(CloudProvider) else 'infra_vms')
        if coll_type == 'templates':
            return getattr(self.collections,
                           'cloud_images' if provider.one_of(CloudProvider) else 'infra_templates')
        else:
            raise ValueError('No support for coll_type: "{}" collection name lookup'
                             .format(coll_type))

    def _switch_migration_ui(self, enable):
        self.update_advanced_settings({'product': {'transformation': enable}})
        self.appliance.server.logout()
        self.evmserverd.restart()
        self.evmserverd.wait_for_running()
        self.wait_for_miq_ready()

    def enable_migration_ui(self):
        if not self.advanced_settings.get('product', {}).get('transformation'):
            self._switch_migration_ui(True)

    def disable_migration_ui(self):
        if self.advanced_settings.get('product', {}).get('transformation'):
            self. _switch_migration_ui(False)

    def set_public_images(self, provider, enabled=False):
        from cfme.cloud.provider.azure import AzureProvider
        provider_type = provider.type_name
        public_image_field = 'get_public_images'
        if provider.one_of(AzureProvider):
            public_image_field = 'get_market_images'
        self.update_advanced_settings({'ems_refresh': {provider_type: {
            public_image_field: enabled}}})
        return True


class Appliance(IPAppliance):
    """Appliance represents an already provisioned cfme appliance vm

    **DO NOT INSTANTIATE DIRECTLY - USE :py:meth:`from_provider`**

    """

    _default_name = 'EVM'

    @property
    def ipapp(self):
        # For backwards compat
        return self

    @classmethod
    def from_provider(cls, provider_key, vm_name, **kwargs):
        """Constructor of this Appliance.

        Retrieves the IP address of the appliance from the provider and then instantiates it,
        adding some extra parameters that are required by this class.

        Args:
            provider_name: Name of the provider this appliance is running under
            vm_name: Name of the VM this appliance is running as
            browser_steal: Setting of the browser_steal attribute.
        """
        from wrapanapi.systems.container import Openshift as OpenShiftSystem
        from cfme.utils.providers import get_mgmt
        from cfme.utils import conf

        provider_mgmt = get_mgmt(provider_key)
        app_kwargs = kwargs.copy()

        if 'hostname' not in app_kwargs:
            def is_ip_available():
                found_ip = None
                try:
                    # TODO: change after openshift wrapanapi refactor
                    if isinstance(provider_mgmt, OpenShiftSystem):
                        found_ip = provider_mgmt.get_ip_address(vm_name)
                    else:
                        vm = provider_mgmt.get_vm(vm_name)
                        vm.ensure_state(VmState.RUNNING)
                        # intentionally taking the time to ping all of these so its recorded
                        potentials = [ip for ip in vm.all_ips if is_pingable(ip)]
                        logger.info('Found reachable IPs for appliance VM, picking first: %s',
                                    potentials)
                        found_ip = potentials[0] if potentials else None
                    # get_ip_address might return None
                    return found_ip if found_ip and resolve_hostname(found_ip) else False
                except (AttributeError, VMInstanceNotFound):
                    return False
            vm_ip, _ = wait_for(is_ip_available,
                              delay=5,
                              num_sec=1200)
            app_kwargs['hostname'] = str(vm_ip)

        if isinstance(provider_mgmt, OpenShiftSystem):
            # there should also be present appliance hostname, container, db_host
            provider_data = conf.cfme_data.management_systems[provider_key]
            provider_creds = conf.credentials[provider_data['credentials']]
            ssh_creds = conf.credentials[provider_data['ssh_creds']]

            if not app_kwargs.get('project'):
                app_kwargs['project'] = vm_name
            app_kwargs['openshift_creds'] = {
                'hostname': provider_data['hostname'],
                'username': provider_creds['username'],
                'password': provider_creds['password'],
                'ssh': {
                    'username': ssh_creds['username'],
                    'password': ssh_creds['password'],
                }
            }

        appliance = cls(**app_kwargs)
        appliance.vm_name = vm_name
        appliance.provider = provider_mgmt
        appliance.provider_key = provider_key
        return appliance

    @logger_wrap("Configure Appliance: {}")
    def configure(self, log_callback=None, on_openstack=False, **kwargs):
        """Configures appliance - database setup, rename, ntp sync

        Utility method to make things easier.

        Args:
            db_address: Address of external database if set, internal database if ``None``
                        (default ``None``)
            name_to_set: Name to set the appliance name to if not ``None`` (default ``None``)
            region: Number to assign to region (default ``0``)
            fix_ntp_clock: Fixes appliance time if ``True`` (default ``True``)
            key_address: Fetch encryption key from this address if set, generate a new key if
                         ``None`` (default ``None``)
            on_openstack: If appliance is running on Openstack provider (default ``False``)
        """
        log_callback(f"Configuring appliance {self.vm_name} on {self.provider_key}")

        # Defer to the IPAppliance.
        super().configure(log_callback=log_callback, on_openstack=on_openstack)

    #  TODO Can we remove this?
    @logger_wrap("Configure fleecing: {}")
    def configure_fleecing(self, log_callback=None):
        with self(browser_steal=True):
            if self.is_on_vsphere:
                self.install_vddk(reboot=True, log_callback=log_callback)
                self.wait_for_miq_ready(log_callback=log_callback)

            if self.is_on_rhev:
                self.add_rhev_direct_lun_disk()

            log_callback('Enabling smart proxy role...')
            roles = self.server.settings.server_roles_db
            if not roles["smartproxy"]:
                self.server.settings.enable_server_roles("smartproxy")

            # add provider
            log_callback('Setting up provider...')
            from cfme.utils.providers import get_crud
            provider = get_crud(self.provider_key, appliance=self)
            provider.setup()

            # credential hosts
            log_callback('Credentialing hosts...')
            if not RUNNING_UNDER_SPROUT:
                provider.setup_hosts_credentials()

            # if rhev, set relationship
            if self.is_on_rhev:
                from cfme.infrastructure.virtual_machines import InfraVm
                log_callback('Setting up CFME VM relationship...')
                vm = self.collections.infra_vms.instantiate(self.vm_name, provider)
                cfme_rel = InfraVm.CfmeRelationship(vm)
                cfme_rel.set_relationship(str(self.server.name), self.server.sid)

    # TODO Remove cached property, could be a lot of references
    @cached_property
    def mgmt(self):
        return self.provider.get_vm(self.vm_name)

    def does_vm_exist(self):
        return self.provider.does_vm_exist(self.vm_name)

    def destroy(self):
        """Destroys the VM this appliance is running as
        """
        if self.is_on_rhev:
            # if rhev, try to remove direct_lun just in case it is detach
            self.remove_rhev_direct_lun_disk()
        if self.does_vm_exist():
            self.mgmt.cleanup()

    def stop(self):
        """Stops the VM this appliance is running as
        """
        self.mgmt.ensure_state(VmState.STOPPED)

    def start(self):
        """Starts the VM this appliance is running as
        """
        self.mgmt.ensure_state(VmState.RUNNING)

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
        self.mgmt.mark_as_template()

    @property
    def is_running(self):
        return self.mgmt.is_running

    @property
    def is_on_rhev(self):
        from cfme.infrastructure.provider.rhevm import RHEVMProvider
        return isinstance(self.provider, RHEVMProvider.mgmt_class)

    @property
    def is_on_vsphere(self):
        from cfme.infrastructure.provider.virtualcenter import VMwareProvider
        return isinstance(self.provider, VMwareProvider.mgmt_class)

    @property
    def is_on_openshift(self):
        from cfme.containers.provider.openshift import OpenshiftProvider
        return isinstance(self.provider, OpenshiftProvider.mgmt_class)

    @logger_wrap("Setting ansible url: {}")
    def set_ansible_url(self, log_callback=None):
        if self.is_on_openshift:
            try:
                config_map = self.provider.get_appliance_tags(self.project)
                url = config_map['cfme-openshift-embedded-ansible']['url']
                tag = config_map['cfme-openshift-embedded-ansible']['tag']
                config = {'embedded_ansible': {'container': {'image_name': url, 'image_tag': tag}}}
                self.update_advanced_settings(config)
            except KeyError as e:
                msg = "embedded ansible url was not changed in appliance {} because of {}".format(
                    self.vm_name, str(e))
                log_callback(msg)

    @property
    def _lun_name(self):
        return f"{self.vm_name}LUNDISK"

    def add_rhev_direct_lun_disk(self, log_callback=None):
        if log_callback is None:
            log_callback = logger.info
        if self.is_dev or not self.is_on_rhev:
            msg = "appliance NOT on rhev or is dev, unable to connect direct_lun"
            log_callback(msg)
            raise ApplianceException(msg)
        log_callback('Adding RHEV direct_lun hook...')
        self.wait_for_ssh()
        try:
            self.mgmt.connect_direct_lun(lun_name=self._lun_name)
        except Exception as e:
            log_callback(f"Appliance {self.vm_name} failed to connect RHEV direct LUN.")
            log_callback(str(e))
            raise

    @logger_wrap("Remove RHEV LUN: {}")
    def remove_rhev_direct_lun_disk(self, log_callback=None):
        if self.is_dev or not self.is_on_rhev:
            msg = "appliance NOT on rhev or is dev, unable to disconnect direct_lun"
            log_callback(msg)
            raise ApplianceException(msg)
        log_callback('Removing RHEV direct_lun hook...')
        self.wait_for_ssh()
        try:
            self.mgmt.disconnect_disk(self._lun_name)
        except Exception as e:
            log_callback(f"Appliance {self.vm_name} failed to connect RHEV direct LUN.")
            log_callback(str(e))
            raise


def provision_appliance(
    provider_name,
    version=None,
    vm_name_prefix='cfme',
    template=None,
    vm_name=None
):
    """Provisions fresh, unconfigured appliance of a specific version

    Note:
        If no matching template for given version is found, and trackerbot is set up,
        the latest available template of the same stream will be used.
        E.g.: if there is no template for 5.10.5.1 but there is 5.10.5.3, it will be used instead.
        If both template name and version are specified, template name takes priority.

    Args:
        provider_name: key of the provider from cfme_data to provision on
        version: version of appliance to provision
        vm_name_prefix: name prefix to use when deploying the appliance vm

    Returns: Unconfigured appliance; instance of :py:class:`Appliance`

    Usage:
        my_appliance = provision_appliance('rhv-43-prov', '5.10.1.8', 'my_tests')
        ...other configuration...
        my_appliance.db.enable_internal()
        my_appliance.wait_for_miq_ready()
        my_appliance.set_ntp_sources()

        or
        my_appliance = provision_appliance('vcenter-65-prov', '5.10.1.8', 'my_tests')
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
        from cfme.utils import trackerbot
        api = trackerbot.api()
        stream = get_stream(version)
        template_data = trackerbot.latest_template(api, stream, provider_name)
        return template_data.get('latest_template')

    if template is not None:
        template_name = template
    elif version is not None:
        # We try to get the latest template from the same stream - if trackerbot is set up
        if conf.env.get('trackerbot', {}):
            template_name = _get_latest_template()
            if not template_name:
                raise ApplianceException('No template found for stream {} on provider {}'
                    .format(get_stream(version), provider_name))
            logger.warning('No template found matching version %s, using %s instead.',
                version, template_name)
        else:
            raise ApplianceException(f'No template found matching version {version}')
    else:
        raise ApplianceException('Either version or template name must be specified')

    prov_data = conf.cfme_data.get('management_systems', {})[provider_name]
    from cfme.utils.providers import get_mgmt
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

    if prov_data["type"] == "scvmm":
        if "host_group" in prov_data.provisioning:
            deploy_args["host_group"] = prov_data.provisioning["host_group"]

    template = provider.get_template(template_name)
    template.deploy(**deploy_args)

    return Appliance.from_provider(provider_name, vm_name, ui_protocol="http")


class ApplianceStack(LocalStack):

    def push(self, obj):
        stack_parent = self.top
        super().push(obj)

        logger.info(f"Pushed appliance hostname [{obj.hostname}] on stack \n"
                    f"Previous stack head was {getattr(stack_parent, 'hostname', 'empty')}")
        if obj.browser_steal:
            from cfme.utils import browser
            browser.start()

    def pop(self):
        stack_parent = super().pop()
        current = self.top
        logger.info(f"Popped appliance {getattr(stack_parent, 'hostname', 'empty')} from stack\n"
                    f"Stack head is {getattr(current, 'hostname', 'empty')}")

        if stack_parent and stack_parent.browser_steal:
            from cfme.utils import browser
            browser.start()
        return stack_parent


stack = ApplianceStack()


def load_appliances(appliance_list, global_kwargs):
    """Instantiate a list of appliances from configuration data.

    Args:
        appliance_list: List of dictionaries that contain parameters for :py:class:`IPAppliance`
        global_kwargs: Arguments that will be defined for each appliances. Appliance can override.

    Result:
        List of :py:class:`IPAppliance`
    """
    result = []
    for idx, appliance_kwargs in enumerate(appliance_list):
        kwargs = {}
        kwargs.update(global_kwargs)
        kwargs.update(appliance_kwargs)

        if kwargs.pop('dummy', False):
            result.append(DummyAppliance(**kwargs))
        else:
            mapping = IPAppliance.CONFIG_MAPPING

            if not any(k in mapping for k in kwargs):
                raise ValueError(
                    f"No valid IPAppliance kwargs found in config for appliance #{idx}"
                )
            appliance = IPAppliance(**{mapping[k]: v for k, v in kwargs.items() if k in mapping})

            result.append(appliance)
    return result


def _version_for_version_or_stream(version_or_stream, sprout_client=None):
    if version_or_stream is attr.NOTHING:
        return attr.fields(DummyAppliance).version.default
    if isinstance(version_or_stream, Version):
        return version_or_stream

    assert isinstance(version_or_stream, str), version_or_stream

    from cfme.test_framework.sprout.client import SproutClient
    sprout_client = SproutClient.from_config() if sprout_client is None else sprout_client

    if version_or_stream[0].isdigit():  # presume streams start with non-number
        return Version(version_or_stream)
    for version_str in sprout_client.available_cfme_versions():
        version = Version(version_str)
        if version.stream() == version_or_stream:
            return version

    raise LookupError(version_or_stream)


def collections_for_appliance(appliance):
    from cfme.modeling.base import EntityCollections
    return EntityCollections.for_appliance(appliance)


@attr.s
class DummyAppliance:
    """a dummy with minimal attribute set"""
    hostname = 'DummyApplianceHostname'
    browser_steal = False
    version = attr.ib(default=Version('5.11.0'), converter=_version_for_version_or_stream)
    is_pod = False
    is_dev = False
    build = 'dummyappliance'
    managed_known_providers = []
    collections = attr.ib(default=attr.Factory(collections_for_appliance, takes_self=True))
    url = 'http://dummies.r.us'
    is_dummy = attr.ib(default=True)

    @property
    def browser(self):
        pytest.xfail("browser not supported with DummyAppliance")

    @property
    def is_downstream(self):
        return not (self.version.is_in_series('master') or self.version.is_in_series('upstream'))

    @classmethod
    def from_config(cls, pytest_config):
        version = pytest_config.getoption('--dummy-appliance-version')
        return cls(version=(version or attr.NOTHING))

    @classmethod
    def from_json(cls, json_string):
        return cls(**json.loads(json_string))

    @property
    def as_json(self):
        """Dumps the arguments that can create this appliance as a JSON. None values are ignored."""
        def _version_tostr(x):
            if isinstance(x, Version):
                return str(x)
            else:
                return x

        return json.dumps({
            k: _version_tostr(getattr(self, k))
            for k in self.__dict__ if k != "collections"})

    def set_session_timeout(self, *k):
        pass

    def __enter__(self):
        """ This method will replace the current appliance in the store """
        stack.push(self)
        return self

    def __exit__(self, *args, **kwargs):
        """This method will remove the appliance from the store"""
        assert stack.pop() is self, 'Dummy appliance on stack inconsistent'


def find_appliance(obj, require=True):
    if isinstance(obj, NavigatableMixin):
        return obj.appliance
    # duck type - either is the config of pytest, or holds it
    config = getattr(obj, 'config', obj)
    from cfme.test_framework.appliance import PLUGIN_KEY
    holder = config.pluginmanager.get_plugin(PLUGIN_KEY)
    if holder or require:
        assert holder
        return holder.held_appliance


def load_appliances_from_config(config):
    """
    Instantiate IPAppliance objects based on data in ``appliances`` section of config.

    The ``config`` contains some global values and ``appliances`` key which contains a list of dicts
    that have the same keys as ``IPAppliance.CONFIG_MAPPING``'s keys.

    The global values in the root of the dict have lesser priority than the values in appliance
    definitions themselves

    Args:
        config: A dictionary with the configuration
    """
    if config.get('appliances', None) is None:
        raise ValueError("Invalid config: missing an 'appliances' section, or its empty")
    appliances = config['appliances']

    global_kwargs = {
        k: config[k]
        for k in IPAppliance.CONFIG_MAPPING.keys()
        if k not in IPAppliance.CONFIG_NONGLOBAL and k in config}

    return load_appliances(appliances, global_kwargs)


class ApplianceSummoningWarning(PendingDeprecationWarning):
    """to ease filtering/erroring on magical appliance creation based on script vs code"""


def get_or_create_current_appliance():
    if stack.top is None:
        warnings.warn(
            "magical creation of appliance objects has been deprecated,"
            " please obtain a appliance object directly",
            category=ApplianceSummoningWarning,
        )
        stack.push(load_appliances_from_config(conf.env)[0])
    return stack.top


current_appliance = LocalProxy(get_or_create_current_appliance)


class _CurrentAppliance:
    def __get__(self, instance, owner):
        return get_or_create_current_appliance()


class NavigatableMixin:
    """NavigatableMixin ensures that an object can navigate properly

    The NavigatableMixin object ensures that a Collection/Entity object inside the
    framework has access to be able to **create** a Widgetastic View, and that it
    has access to the browser.

    Note: The browser access will have to change once proliferation of the Sentaku
          system becomes common place
    """

    @property
    def browser(self):
        return self.appliance.browser.widgetastic

    def create_view(self, view_class, o=None, override=None, wait=None):
        """Create a view object given the class and contextual parameters

        Args:
            view_class (cls): widgetastic.widget.View based class to create an instance of
            o (obj): Entity object that is the context for the view class (normally linked by nav)
            override (dict): Dictionary of override values for the contextual object (o)
            wait: Value to pass to wait_displayed, default of None skips wait_displayed check
        """
        o = o or self
        if override is not None:
            new_obj = copy(o)
            new_obj.__dict__.update(override)
        else:
            new_obj = o

        view = self.appliance.browser.create_view(view_class,
                                                  additional_context={'object': new_obj})
        if wait:
            view.wait_displayed(timeout=wait)
        return view

    def list_destinations(self):
        """This function returns a list of all valid destinations for a particular object
        """
        return {
            impl.name: impl.navigator.list_destinations(self)
            for impl in self.appliance.context.implementations.values()
            if impl.navigator
        }


class NavigatableDeprecationWarning(DeprecationWarning):
    pass


warnings.simplefilter('ignore', NavigatableDeprecationWarning)


@removals.removed_class(
    "Navigatable", message=("Navigatable is being deprecated in favour of using Collections "
                            "objects with the NavigatableMixin"),
    category=NavigatableDeprecationWarning,
)
class Navigatable(NavigatableMixin):

    appliance = _CurrentAppliance()

    def __init__(self, appliance=None):
        self.appliance = appliance or get_or_create_current_appliance()


class MiqImplementationContext(sentaku.ImplementationContext):
    """ Our context for Sentaku"""
    pass
