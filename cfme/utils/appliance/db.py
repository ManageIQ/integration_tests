import attr
from cached_property import cached_property
import fauxfactory
from textwrap import dedent

from cfme.utils import db, conf, clear_property_cache, datafile
from cfme.utils.path import scripts_path
from cfme.utils.wait import wait_for

from .plugin import AppliancePlugin, AppliancePluginException


class ApplianceDBException(AppliancePluginException):
    """Basic Exception for Appliance DB object"""
    pass


@attr.s
class ApplianceDB(AppliancePlugin):
    """Holder for appliance DB related methods and functions"""
    _ssh_client = attr.ib(default=None)

    # Until this needs a version pick, make it an attr
    postgres_version = 'rh-postgresql95'
    service_name = '{}-postgresql'.format(postgres_version)

    @cached_property
    def client(self):
        # slightly crappy: anything that changes self.address should also del(self.client)
        return db.Db(self.address)

    @cached_property
    def address(self):
        # pulls the db address from the appliance by default, falling back to the appliance
        # ip address (and issuing a warning) if that fails. methods that set up the internal
        # db should set db_address to something else when they do that
        if self.appliance.db_host:
            return self.appliance.db_host
        try:
            db_addr = self.appliance.wait_for_host_address()
            if db_addr is None:
                return self.appliance.address
            db_addr = db_addr.strip()
            ip_addr = self.appliance.ssh_client.run_command('ip address show')
            if db_addr in ip_addr.output or db_addr.startswith('127') or 'localhost' in db_addr:
                # address is local, use the appliance address
                return self.appliance.address
            else:
                return db_addr
        except (IOError, KeyError) as exc:
            self.logger.error('Unable to pull database address from appliance')
            self.logger.error(exc)
            return self.appliance.address

    @property
    def is_partition_extended(self):
        return self.appliance.ssh_client.run_command(
            "ls /var/www/miq/vmdb/.db_partition_extended") == 0

    def extend_partition(self):
        """Extends the /var partition with DB while shrinking the unused /repo partition"""
        if self.is_partition_extended:
            return
        with self.appliance.ssh_client as ssh:
            rc, out = ssh.run_command("df -h")
            self.logger.info("File systems before extending the DB partition:\n{}".format(out))
            ssh.run_command("umount /repo")
            ssh.run_command("lvreduce --force --size -9GB /dev/mapper/VG--CFME-lv_repo")
            ssh.run_command("mkfs.xfs -f /dev/mapper/VG--CFME-lv_repo")
            ssh.run_command("lvextend --resizefs --size +9GB /dev/mapper/VG--CFME-lv_var")
            ssh.run_command("mount -a")
            rc, out = ssh.run_command("df -h")
            self.logger.info("File systems after extending the DB partition:\n{}".format(out))
            ssh.run_command("touch /var/www/miq/vmdb/.db_partition_extended")

    def drop(self):
        """ Drops the vmdb_production database

            Note: EVM service has to be stopped for this to work.
        """
        def _db_dropped():
            rc, out = self.appliance.ssh_client.run_command(
                'systemctl restart {}-postgresql'.format(self.postgres_version), timeout=60)
            assert rc == 0, "Failed to restart postgres service: {}".format(out)
            self.appliance.ssh_client.run_command('dropdb vmdb_production', timeout=15)
            rc, out = self.appliance.ssh_client.run_command(
                "psql -l | grep vmdb_production | wc -l", timeout=15)
            return rc == 0
        wait_for(_db_dropped, delay=5, timeout=60, message="drop the vmdb_production DB")

    @property
    def ssh_client(self, **connect_kwargs):
        # Not lazycached to allow for the db address changing
        if self.is_internal:
            return self.appliance.ssh_client
        else:
            if self._ssh_client is None:
                self._ssh_client = self.appliance.ssh_client(hostname=self.address)
            return self._ssh_client

    def backup(self, database_path="/tmp/evm_db.backup"):
        """Backup VMDB database

        """
        from . import ApplianceException
        self.logger.info('Backing up database')
        status, output = self.appliance.ssh_client.run_rake_command(
            'evm:db:backup:local --trace -- --local-file "{}" --dbname vmdb_production'.format(
                database_path))
        if status != 0:
            msg = 'Failed to backup database'
            self.logger.error(msg)
            raise ApplianceException(msg)

    def restore(self, database_path="/tmp/evm_db.backup"):
        """Restore VMDB database

        """
        from . import ApplianceException
        self.logger.info('Restoring database')
        status, output = self.appliance.ssh_client.run_rake_command(
            'evm:db:restore:local --trace -- --local-file "{}"'.format(database_path))
        if status != 0:
            msg = 'Failed to restore database on appl {}, output is {}'.format(self.address,
                output)
            self.logger.error(msg)
            raise ApplianceException(msg)
        if self.appliance.version > '5.8':
            status, output = self.ssh_client.run_command("fix_auth --databaseyml -i {}".format(
                conf.credentials['database'].password), timeout=45)
            if status != 0:
                self.logger.error("Failed to change invalid db password: {}".format(output))

    def setup(self, **kwargs):
        """Configure database

        On downstream appliances, invokes the internal database setup.
        On all appliances waits for database to be ready.

        """
        self.logger.info('Starting DB setup')
        if self.appliance.is_downstream:
            # We only execute this on downstream appliances.
            self.enable_internal(**kwargs)
        elif not self.appliance.evmserverd.running:
            self.appliance.evmserverd.start()
            self.appliance.evmserverd.enable()  # just to be sure here.
            self.appliance.wait_for_web_ui()

        # Make sure the database is ready
        wait_for(func=lambda: self.is_ready,
            message='appliance db ready', delay=20, num_sec=1200)

        self.logger.info('DB setup complete')

    def loosen_pgssl(self, with_ssl=False):
        """Loosens postgres connections"""

        self.logger.info('Loosening postgres permissions')

        # Init SSH client
        client = self.appliance.ssh_client

        # set root password
        cmd = "psql -d vmdb_production -c \"alter user {} with password '{}'\"".format(
            conf.credentials['database']['username'], conf.credentials['database']['password']
        )
        client.run_command(cmd)

        # back up pg_hba.conf
        scl = self.postgres_version
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
        status, out = client.run_command("systemctl restart {scl}-postgresql".format(scl=scl))
        return status

    def enable_internal(self, region=0, key_address=None, db_password=None, ssh_password=None,
                        db_disk=None):
        """Enables internal database

        Args:
            region: Region number of the CFME appliance.
            key_address: Address of CFME appliance where key can be fetched.
            db_disk: Path of the db disk for --dbdisk appliance_console_cli. If not specified it
                     tries to load it from the appliance.

        Note:
            If key_address is None, a new encryption key is generated for the appliance.
        """
        # self.logger.info('Enabling internal DB (region {}) on {}.'.format(region, self.address))
        self.address = self.appliance.address
        clear_property_cache(self, 'client')

        client = self.ssh_client

        # Defaults
        db_password = db_password or conf.credentials['database']['password']
        ssh_password = ssh_password or conf.credentials['ssh']['password']
        if not db_disk:
            try:
                db_disk = self.appliance.unpartitioned_disks[0]
            except IndexError:
                db_disk = None
                self.logger.warning(
                    'Failed to set --dbdisk from the appliance. On 5.9.0.3+ it will fail.')

        if self.appliance.has_cli:
            base_command = 'appliance_console_cli --region {}'.format(region)
            # use the cli
            if key_address:
                command_options = ('--internal --fetch-key {key} -p {db_pass} -a {ssh_pass}'
                                   .format(key=key_address, db_pass=db_password,
                                           ssh_pass=ssh_password))

            else:
                command_options = '--internal --force-key -p {db_pass}'.format(db_pass=db_password)

            if db_disk:
                command_options = ' '.join([command_options, '--dbdisk {}'.format(db_disk)])

            status, out = client.run_command(' '.join([base_command, command_options]))
            if status != 0 or 'failed' in out.lower():
                raise Exception('Could not set up the database:\n{}'.format(out))
        else:
            # no cli, use the enable internal db script
            rbt_repl = {
                'miq_lib': '/var/www/miq/lib',
                'region': region,
                'postgres_version': self.postgres_version
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

        self.logger.info('Output from appliance db configuration: %s', out)

        return status, out

    def enable_external(self, db_address, region=0, db_name=None, db_username=None,
                        db_password=None):
        """Enables external database

        Args:
            db_address: Address of the external database
            region: Number of region to join
            db_name: Name of the external DB
            db_username: Username to access the external DB
            db_password: Password to access the external DB

        Returns a tuple of (exitstatus, script_output) for reporting, if desired
        """
        self.logger.info('Enabling external DB (db_address {}, region {}) on {}.'
            .format(db_address, region, self.address))
        # reset the db address and clear the cached db object if we have one
        self.address = db_address
        clear_property_cache(self, 'client')

        # default
        db_name = db_name or 'vmdb_production'
        db_username = db_username or conf.credentials['database']['username']
        db_password = db_password or conf.credentials['database']['password']

        client = self.ssh_client

        if self.appliance.has_cli:
            # copy v2 key
            master_client = client(hostname=self.address)
            rand_filename = "/tmp/v2_key_{}".format(fauxfactory.gen_alphanumeric())
            master_client.get_file("/var/www/miq/vmdb/certs/v2_key", rand_filename)
            client.put_file(rand_filename, "/var/www/miq/vmdb/certs/v2_key")

            # enable external DB with cli
            status, out = client.run_command(
                'appliance_console_cli '
                '--hostname {0} --region {1} --dbname {2} --username {3} --password {4}'.format(
                    self.address, region, db_name, db_username, db_password
                )
            )
        else:
            # no cli, use the enable external db script
            rbt_repl = {
                'miq_lib': '/var/www/miq/lib',
                'host': self.address,
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
            self.logger.error('error enabling external db')
            self.logger.error(out)
            msg = ('Appliance {} failed to enable external DB running on {}'
                  .format(self.appliance.address, db_address))
            self.logger.error(msg)
            from . import ApplianceException
            raise ApplianceException(msg)

        return status, out

    @property
    def is_dedicated_active(self):
        return_code, output = self.appliance.ssh_client.run_command(
            "systemctl status {}-postgresql.service | grep running".format(
                self.postgres_version))
        return return_code == 0

    def wait_for(self, timeout=600):
        """Waits for appliance database to be ready

        Args:
            timeout: Number of seconds to wait until timeout (default ``180``)
        """
        wait_for(func=lambda: self.is_ready,
                 message='appliance.db.is_ready',
                 delay=20,
                 num_sec=timeout)

    @property
    def is_enabled(self):
        """Is database enabled"""
        if self.address is None:
            return False
        return True

    @property
    def is_internal(self):
        """Is database internal"""
        if self.address == self.appliance.address:
            return True
        return False

    @property
    def is_ready(self):
        """Is database ready"""
        # Using 'and' chain instead of all(...) to
        # prevent calling more things after a step fails
        return self.is_online and self.has_database and self.has_tables

    @property
    def is_online(self):
        """Is database online"""
        db_check_command = ('psql -U postgres -t  -c "select now()" postgres')
        result = self.ssh_client.run_command(db_check_command)
        return result.rc == 0

    @property
    def has_database(self):
        """Does database have a database defined"""
        db_check_command = ('psql -U postgres -t  -c "SELECT datname FROM pg_database '
            'WHERE datname LIKE \'vmdb_%\';" postgres | grep -q vmdb_production')
        result = self.ssh_client.run_command(db_check_command)
        return result.rc == 0

    @property
    def has_tables(self):
        """Does database have tables defined"""
        db_check_command = ('psql -U postgres -t  -c "SELECT * FROM information_schema.tables '
            'WHERE table_schema = \'public\';" vmdb_production | grep -q vmdb_production')
        result = self.ssh_client.run_command(db_check_command)
        return result.rc == 0

    def start_db_service(self):
        """Starts the postgresql service via systemctl"""
        self.logger.info('Starting service: {}'.format(self.service_name))
        with self.ssh_client as ssh:
            result = ssh.run_command('systemctl start {}'.format(self.service_name))
            assert result.success, 'Failed to start {}'.format(self.service_name)
            self.logger.info('Started service: {}'.format(self.service_name))

    def stop_db_service(self):
        """Starts the postgresql service via systemctl"""
        service = '{}-postgresql'.format(self.postgres_version)
        self.logger.info('Stopping {}'.format(service))
        with self.ssh_client as ssh:
            result = ssh.run_command('systemctl stop {}'.format(self.service_name))
            assert result.success, 'Failed to stop {}'.format(service)
            self.logger.info('Stopped {}'.format(service))
