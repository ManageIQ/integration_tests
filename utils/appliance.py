import atexit
import os
import random
import shutil
import subprocess
from textwrap import dedent
from tempfile import mkdtemp
from urlparse import urlparse

import requests
from time import sleep

from utils import conf, datafile, db, lazycache
from utils.browser import browser_session
from utils.log import logger, create_sublogger
from utils.net import net_check
from utils.path import data_path, scripts_path
from utils.providers import provider_factory
from utils.randomness import generate_random_string
from utils.ssh import SSHClient
from utils.version import get_version, LATEST
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
            key_address: Fetch encryption key from this address if set, generate a new key if
                         ``None`` (default ``None``)

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

    def browser_session(self, reset_cache=False):
        return self.ipapp.browser_session(reset_cache=reset_cache)


class IPAppliance(object):
    """IPAppliance represents an already provisioned cfme appliance whos provider is unknown
    but who has an IP address. This has a lot of core functionality that Appliance uses, since
    it knows both the provider, vm_name and can there for derive the IP address.

    Args:
        ipaddress: The IP address of the provider
    """

    def __init__(self, address=None):
        if address is not None:
            self.address = address

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, repr(self.address))

    @classmethod
    def from_url(ip_appliance_class, url):
        if url is None:
            url = conf.env['base_url']
        parsed_url = urlparse(url)
        ip_a = ip_appliance_class(parsed_url.hostname)
        # stash the passed-in url in the lazycache to save a step
        ip_a.url = url
        return ip_a

    @lazycache
    def address(self):
        # If address wasn't set in __init__, use the hostname from base_url
        parsed_url = urlparse(conf.env['base_url'])
        return parsed_url.hostname

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
        connect_kwargs['username'] = connect_kwargs.get('username',
            conf.credentials['ssh']['username'])
        connect_kwargs['password'] = connect_kwargs.get('password',
            conf.credentials['ssh']['password'])
        return SSHClient(**connect_kwargs)

    def fix_ntp_clock(self):
        """Fixes appliance time using ntpdate on appliance"""
        self.log.info('fixing appliance clock')
        client = self.ssh_client()
        try:
            ntp_server = random.choice(conf.cfme_data['clock_servers'])
        except IndexError:
            raise Exception('No clock servers configured in cfme_data.yaml')

        status, out = client.run_command("ntpdate {}".format(ntp_server))
        if status != 0:
            self.log.error('ntpdate failed:')
            self.log.error(out)
            raise Exception('Setting the time failed on appliance')

    def precompile_assets(self):
        """Precompile the static assets (images, css, etc) on an appliance

        Not required on 5.2 appliances

        """
        # compile assets if required (not required on 5.2)
        if self.version.is_in_series("5.2"):
            return

        self.log.info('precompiling assets')

        client = self.ssh_client()
        status, out = client.run_rake_command("assets:precompile")

        if status != 0:
            raise ApplianceException('Appliance {} failed to precompile assets'.format(
                self.address))
        else:
            self.restart_evm_service()

        return status

    def clone_domain(self, source="ManageIQ", dest="Default"):
        """Clones Automate domain

        Args:
            src: Source domain name.
            dst: Destination domain name.

        Note:
            Not required (and does not do anything) on 5.2 appliances

        """
        if self.version.is_in_series("5.2"):
            return

        self.log.info('cloning automate domain')

        client = self.ssh_client()

        # Make sure the database is ready
        self.wait_for_db()

        # Make sure the working dir exists
        client.run_command('mkdir -p /tmp/miq')

        self.log.info('Exporting domain...')
        export_opts = 'DOMAIN={} EXPORT_DIR=/tmp/miq PREVIEW=false OVERWRITE=true'.format(source)
        export_cmd = 'evm:automate:export {}'.format(export_opts)
        self.log.info(export_cmd)
        status, output = client.run_rake_command(export_cmd)
        if status != 0:
            raise ApplianceException('Failed to export {} domain'.format(source))

        ro_fix_cmd = "sed -i 's/system: true/system: false/g' /tmp/miq/ManageIQ/__domain__.yaml"
        status, output = client.run_command(ro_fix_cmd)
        if status != 0:
            raise ApplianceException('Setting {} domain to read/write failed'.format(dest))

        import_opts = 'DOMAIN={} IMPORT_DIR=/tmp/miq PREVIEW=false'.format(source)
        import_opts += ' OVERWRITE=true IMPORT_AS={}'.format(dest)
        import_cmd = 'evm:automate:import {}'.format(import_opts)
        self.log.info(import_cmd)
        status, output = client.run_rake_command(import_cmd)
        if status != 0:
            raise ApplianceException('Failed to import {} domain'.format(dest))

        return status, output

    def deploy_merkyl(self, start=False):
        """Deploys the Merkyl log relay service to the appliance"""
        self.log.info('deploying merkyl')
        client = self.ssh_client()

        client.run_command('mkdir -p /root/merkyl')
        for filename in ['__init__.py', 'merkyl.tpl', ('bottle.py.dontflake', 'bottle.py'),
                'allowed.files']:
            try:
                src, dest = filename
            except (TypeError, ValueError):
                # object is not iterable or too many values to unpack
                src = dest = filename
            self.log.info('sending {} to appliance'.format(src))
            client.put_file(data_path.join('bundles', 'merkyl', src).strpath,
                os.path.join('/root/merkyl', dest))

        client.put_file(data_path.join('bundles', 'merkyl', 'merkyl').strpath,
            os.path.join('/etc/init.d/merkyl'))
        client.run_command('chmod 775 /etc/init.d/merkyl')
        client.run_command(
            '/bin/bash -c \'if ! [[ $(iptables -L -n | grep "state NEW tcp dpt:8192") ]]; then '
            'iptables -I INPUT 6 -m state --state NEW -m tcp -p tcp --dport 8192 -j ACCEPT; fi\'')

        if start:
            client.run_command('service merkyl restart')

    def update_rhel(self, *urls, **kwargs):
        """Update RHEL on appliance"""
        self.log.info('updating appliance')
        if not urls:
            urls = [conf.cfme_data['basic_info']['rhel_updates_url']]
            if self.version.is_in_series("5.3"):
                try:
                    urls.append(conf.cfme_data['basic_info']['rhscl_updates_url'])
                except KeyError:
                    pass

        client = self.ssh_client()

        # create repo file
        self.log.info('Creating repo file on appliance')
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
            raise Exception('Failed to write repo updates repo to appliance')

        # update
        self.log.info('Running rhel updates on appliance')
        status, out = client.run_command('yum update -y --nogpgcheck')
        if status != 0:
            self.log.error('appliance update failed')
            self.log.error(out)
            raise ApplianceException('Appliance {} failed to update RHEL, error in logs'.format(
                self.address))

        return status, out

    def patch_ajax_wait(self, reverse=False):
        """Patches ajax wait code

        Args:
            reverse: Will reverse the ajax wait code patch if set to ``True``

        Note:
            Does nothing for versions including and above 5.3

        """
        if self.version >= '5.3':
            return

        self.log.info('patching appliance')

        # Find the patch file
        patch_file_name = datafile.data_path_for_filename('ajax_wait.diff', scripts_path.strpath)

        # Set up temp dir
        tmpdir = mkdtemp()
        atexit.register(shutil.rmtree, tmpdir)
        source = '/var/www/miq/vmdb/public/javascripts/application.js'
        target = os.path.join(tmpdir, 'application.js')

        client = self.ssh_client()
        self.log.info('retriving appliance.js from appliance')
        client.get_file(source, target)

        os.chdir(tmpdir)
        # patch, level 4, patch direction (default forward), ignore whitespace, don't output rejects
        direction = '-N -R' if reverse else '-N'
        exitcode = subprocess.call('patch -p4 %s -l -r- < %s' % (direction, patch_file_name),
            shell=True)

        if exitcode == 0:
            # Put it back after successful patching.
            self.log.info('replacing appliance.js on appliance')
            client.put_file(target, source)
        else:
            self.log.info('patch failed, not changing appliance')

        return exitcode

    def loosen_pgssl(self, with_ssl=False):
        """Loosens postgres connections

        Note:
            Not required (and does not do anything) on 5.2 appliances

        """
        if self.version.is_in_series("5.2"):
            return

        self.log.info('loosening postgres permissions')

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

    def browser_session(self, reset_cache=False):
        """Creates browser session connected to this appliance

        Returns: Browser session connected to this appliance.

        Usage:
            with appliance.browser_session() as browser:
                browser.do_stuff(TM)
        """
        return browser_session(base_url=self.url, reset_cache=reset_cache)

    def enable_internal_db(self, region=0, key_address=None, db_password=None,
                           ssh_password=None):
        """Enables internal database

        Args:
            region: Region number of the CFME appliance.
            key_address: Address of CFME appliance where key can be fetched.

        Note:
            If key_address is None, a new encryption key is generated for the appliance.
        """
        self.log.info('Enabling internal DB (region {}) on {}.'.format(region, self.address))
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
                    'appliance_console_cli --region {} --internal -f {} -p {} -a {}'
                    .format(region, key_address, db_password, ssh_password)
                )
            else:
                status, out = client.run_command(
                    'appliance_console_cli --region {} --internal -k -p {}'
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
            db_username=None, db_password=None):
        """Enables external database

        Args:
            db_address: Address of the external database
            region: Number of region to join
            db_name: Name of the external DB
            db_username: Username to access the external DB
            db_password: Password to access the external DB

        Returns a tuple of (exitstatus, script_output) for reporting, if desired
        """
        self.log.info('Enabling external DB (db_address {}, region {}) on {}.'
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
            raise ApplianceException('Appliance {} failed to enable external DB running on {}'
                .format(self.address, db_address))

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

    def restart_evm_service(self):
        """Restarts the ``evmserverd`` service on this appliance
        """
        self.log.info('restarting evm service')
        with self.ssh_client() as ssh:
            status, msg = ssh.run_command('service evmserverd restart')
            if status != 0:
                raise ApplianceException('Failed to restart evmserverd service on {}\nError: {}'
                                         .format(self.address, msg))

    def reboot(self, wait_for_web_ui=True):
        self.log.info('rebooting appliance')
        client = self.ssh_client()

        old_uptime = client.uptime()
        status, out = client.run_command('reboot')

        wait_for(lambda: client.uptime() < old_uptime, handle_exception=True,
            num_sec=300, message='appliance to reboot', delay=10)

        if wait_for_web_ui:
            self.wait_for_web_ui()

    def wait_for_web_ui(self, timeout=900, running=True):
        """Waits for the web UI to be running / to not be running

        Args:
            timeout: Number of seconds to wait until timeout (default ``600``)
            running: Specifies if we wait for web UI to start or stop (default ``True``)
                     ``True`` == start, ``False`` == stop
        """
        result, wait = wait_for(self._check_appliance_ui_wait_fn, num_sec=timeout,
            fail_condition=not running, delay=10)
        return result

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

    @property
    def is_ssh_running(self, force=False):
        return net_check(22, self.address, force)

    @property
    def has_cli(self):
        if self.ssh_client().run_command('ls -l /bin/appliance_console_cli')[0] == 0:
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
