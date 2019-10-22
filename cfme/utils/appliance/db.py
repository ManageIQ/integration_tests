import attr
import fauxfactory
from cached_property import cached_property

from cfme.utils import clear_property_cache
from cfme.utils import conf
from cfme.utils import datafile
from cfme.utils import db
from cfme.utils.appliance.plugin import AppliancePlugin
from cfme.utils.appliance.plugin import AppliancePluginException
from cfme.utils.conf import credentials
from cfme.utils.path import scripts_path
from cfme.utils.version import LOWEST
from cfme.utils.version import VersionPicker
from cfme.utils.wait import wait_for


class ApplianceDBException(AppliancePluginException):
    """Basic Exception for Appliance DB object"""
    pass


@attr.s
class ApplianceDB(AppliancePlugin):
    """Holder for appliance DB related methods and functions"""
    _ssh_client = attr.ib(default=None)

    @cached_property
    def service_name(self):
        return VersionPicker({
            LOWEST: 'rh-postgresql95-postgresql',
            '5.11': 'postgresql'}).pick(self.appliance.version)

    @property
    def pg_prefix(self):
        return '/opt/rh/rh-postgresql95/root' if self.appliance.version < '5.11' else ''

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
            db_addr = (
                self.appliance.wait_for_host_address()
                if self.appliance.evmserverd.is_active
                else None
            )
            if db_addr is None:
                return self.appliance.hostname
            db_addr = db_addr.strip()
            ip_addr = self.appliance.ssh_client.run_command('ip address show')
            if db_addr in ip_addr.output or db_addr.startswith('127') or 'localhost' in db_addr:
                # address is local, use the appliance address
                return self.appliance.hostname
            else:
                return db_addr
        except (IOError, KeyError) as exc:
            self.logger.error('Unable to pull database address from appliance')
            self.logger.error(exc)
            return self.appliance.hostname

    @property
    def is_partition_extended(self):
        return self.appliance.ssh_client.run_command(
            "ls /var/www/miq/vmdb/.db_partition_extended") == 0

    def extend_partition(self):
        """Extends the /var partition with DB while shrinking the unused /repo partition"""
        if self.appliance.version < '5.8.1':
            if self.is_partition_extended:
                return
            with self.appliance.ssh_client as ssh:
                result = ssh.run_command("df -h")
                self.logger.info("File systems before extending the DB partition:\n{}"
                                 .format(result.output))
                ssh.run_command("umount /repo")
                ssh.run_command("lvreduce --force --size -9GB /dev/mapper/VG--CFME-lv_repo")
                ssh.run_command("mkfs.xfs -f /dev/mapper/VG--CFME-lv_repo")
                ssh.run_command("lvextend --resizefs --size +9GB /dev/mapper/VG--CFME-lv_var")
                ssh.run_command("mount -a")
                result = ssh.run_command("df -h")
                self.logger.info("File systems after extending the DB partition:\n{}"
                                 .format(result.output))
                ssh.run_command("touch /var/www/miq/vmdb/.db_partition_extended")

    def drop(self):
        """ Drops the vmdb_production database

            Note: EVM service has to be stopped for this to work.
        """

        self.appliance.db_service.restart()
        self.appliance.ssh_client.run_command('dropdb vmdb_production', timeout=15)

        def _db_dropped():
            result = self.appliance.ssh_client.run_command(
                "psql -l | grep vmdb_production | wc -l", timeout=15)
            return result.success
        wait_for(_db_dropped, delay=5, timeout=60, message="drop the vmdb_production DB")

    def create(self):
        """ Creates new vmdb_production database

            Note: EVM service has to be stopped for this to work.
        """
        result = self.appliance.ssh_client.run_command('createdb vmdb_production', timeout=30)
        assert result.success, "Failed to create clean database: {}".format(result.output)

    def migrate(self):
        """migrates a given database and updates REGION/GUID files"""
        ssh = self.ssh_client
        result = ssh.run_rake_command("db:migrate", timeout=300)
        assert result.success, "Failed to migrate new database: {}".format(result.output)
        result = ssh.run_rake_command(
            r'db:migrate:status 2>/dev/null | grep "^\s*down"', timeout=30)
        assert result.failed, ("Migration failed; migrations in 'down' state found: {}"
                               .format(result.output))
        # fetch GUID and REGION from the DB and use it to replace data in /var/www/miq/vmdb/GUID
        # and /var/www/miq/vmdb/REGION respectively
        data_query = {
            'guid': 'select guid from miq_servers',
            'region': 'select region from miq_regions'
        }
        for data_type, db_query in data_query.items():
            data_filepath = '/var/www/miq/vmdb/{}'.format(data_type.upper())
            result = ssh.run_command(
                'psql -d vmdb_production -t -c "{}"'.format(db_query), timeout=15)
            assert result.success, "Failed to fetch {}: {}".format(data_type, result.output)
            db_data = result.output.strip()
            assert db_data, "No {} found in database; query '{}' returned no records".format(
                data_type, db_query)
            result = ssh.run_command(
                "echo -n '{}' > {}".format(db_data, data_filepath), timeout=15)
            assert result.success, "Failed to replace data in {} with '{}': {}".format(
                data_filepath, db_data, result.output)

    def automate_reset(self):
        result = self.ssh_client.run_rake_command("evm:automate:reset", timeout=300)
        assert result.success, "Failed to reset automate: {}".format(result.output)

    def fix_auth_key(self):
        result = self.ssh_client.run_command("fix_auth -i invalid", timeout=45)
        assert result.success, "Failed to change invalid passwords: {}".format(result.output)
        # fix db password

    def fix_auth_dbyml(self):
        result = self.ssh_client.run_command("fix_auth --databaseyml -i {}".format(
            credentials['database']['password']), timeout=45)
        assert result.success, "Failed to change invalid password: {}".format(result.output)

    def reset_user_pass(self):
        result = self.ssh_client.run_rails_command(
            '"u = User.find_by_userid(\'admin\'); u.password = \'{}\'; u.save!"'
            .format(self.appliance.user.credential.secret))
        assert result.success, "Failed to change UI password of {} to {}:" \
            .format(self.appliance.user.credential.principal,
                    self.appliance.user.credential.secret, result.output)

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
        Changed from Rake task due to a bug in 5.9

        """
        from cfme.utils.appliance import ApplianceException
        self.logger.info('Backing up database')
        result = self.appliance.ssh_client.run_command(
            'pg_dump --format custom --file {} vmdb_production'.format(
                database_path))
        if result.failed:
            msg = 'Failed to backup database'
            self.logger.error(msg)
            raise ApplianceException(msg)

    def restore(self, database_path="/tmp/evm_db.backup"):
        """Restore VMDB database

        """
        from cfme.utils.appliance import ApplianceException
        self.logger.info('Restoring database')
        result = self.appliance.ssh_client.run_rake_command(
            'evm:db:restore:local --trace -- --local-file "{}"'.format(database_path))
        if result.failed:
            msg = 'Failed to restore database on appl {}, output is {}'.format(self.address,
                result.output)
            self.logger.error(msg)
            raise ApplianceException(msg)
        result = self.ssh_client.run_command(
            "fix_auth --databaseyml -i {}".format(
                conf.credentials["database"].password
            ),
            timeout=45,
        )
        if result.failed:
            self.logger.error(
                "Failed to change invalid db password: {}".format(result.output)
            )

    def setup(self, **kwargs):
        """Configure database

        On downstream appliances, invokes the internal database setup.
        On all appliances waits for database to be ready.

        """
        key_address = kwargs.pop('key_address', None)
        db_address = kwargs.pop('db_address', None)
        self.logger.info('Starting DB setup')
        is_pod = kwargs.pop('is_pod', False)

        if is_pod:
            self.enable_external(db_address=db_address, **kwargs)
        else:
            self.enable_internal(key_address=key_address, **kwargs)

        # Make sure the database is ready
        wait_for(func=lambda: self.is_ready,
            message='appliance db ready', delay=20, num_sec=1200)

        self.logger.info('DB setup complete')

    def _run_cmd_show_output(self, cmd):
        """
        A small helper to run an ssh command and print return code/output
        """
        with self.ssh_client as client:
            result = client.run_command(cmd)

        # Indent the output by 1 tab (makes it easier to read...)
        if str(result):
            output = str(result)
            output = '\n'.join(['\t{}'.format(line) for line in output.splitlines()])
        else:
            output = ""
        self.logger.info("Return code: %d, Output:\n%s", result.rc, output)
        return result

    def _find_disk_with_free_space(self, needed_size):
        """Find a disk that has >=needed_size free space using parted

        Returns tuple with (disk_name, start GB, end GB, size GB)
        Returns tuples of Nones if a disk with free space is not found

        ----Example parted output with no free space---

        $ parted /dev/vda unit GB print free
        Model: Virtio Block Device (virtblk)
        Disk /dev/vda: 42.9GB
        Sector size (logical/physical): 512B/512B
        Partition Table: msdos
        Disk Flags:

        Number  Start   End     Size    Type     File system  Flags
                0.00GB  0.00GB  0.00GB           Free Space
        1      0.00GB  1.07GB  1.07GB  primary  xfs          boot
        2      1.07GB  42.9GB  41.9GB  primary               lvm


        ----Example parted output with free space----

        $ parted /dev/vda unit GB print free
        Model: Virtio Block Device (virtblk)
        Disk /dev/vda: 75.2GB
        Sector size (logical/physical): 512B/512B
        Partition Table: msdos
        Disk Flags:

        Number  Start   End     Size    Type     File system  Flags
                0.00GB  0.00GB  0.00GB           Free Space
        1      0.00GB  1.07GB  1.07GB  primary  xfs          boot
        2      1.07GB  42.9GB  41.9GB  primary               lvm
                42.9GB  75.2GB  32.2GB           Free Space
        """
        disk_name = start = end = size = None

        for disk in self.appliance.disks:
            result = self._run_cmd_show_output('parted {} unit GB print free'.format(disk))
            if result.failed:
                self.logger.error("Unable to run 'parted' on disk %s, skipping...", disk)
                continue
            lines = str(result).splitlines()
            free_space_lines = [line for line in lines if 'Free Space' in line]

            found_enough_space = False
            for line in free_space_lines:
                gb_data = [float(word.strip('GB')) for word in line.split() if 'GB' in word]
                if len(gb_data) != 3:
                    self.logger.info(
                        "Unable to get free space start/end/size on disk %s, skipping...", disk)
                    continue
                start, end, size = gb_data[0], gb_data[1], gb_data[2]
                if size >= needed_size:
                    disk_name = disk
                    found_enough_space = True
                    self.logger.info("Found %dGB free space available on disk %s", size, disk)
                    break

            if found_enough_space:
                # Stop iterating through the disks, we've found enough space.
                break
            self.logger.info(
                "Free space is less than %dGB on disk %s", needed_size, disk)

        return (disk_name, start, end, size)

    def _create_partition_from_free_space(self, needed_size):
        """
        Create a partition on the disk with free space

        Return the new partition name, or None if this fails
        """
        needed_size = needed_size + 0.5  # make partition a little larger than LVM
        disk, start, end, size = self._find_disk_with_free_space(needed_size)
        if not disk:
            self.logger.error("Unable to find a disk with enough free space!")
            return

        self.logger.info("Creating new LVM for db using free space on %s...", disk)

        if size > needed_size:
            # We don't need to take more of the free space than this...
            end = start + needed_size

        # Save the old partition list so we can figure out what the name of the new one is
        old_disks_and_parts = self.appliance.disks_and_partitions

        result = self._run_cmd_show_output(
            'parted {} --script mkpart primary {}GB {}GB'.format(disk, start, end))
        if result.failed:
            self.logger.error("Creating partition failed, aborting LVM creation!")
            return

        new_disks_and_parts = self.appliance.disks_and_partitions
        diff = [d for d in new_disks_and_parts if d not in old_disks_and_parts]
        if not diff or len(diff) > 1:
            self.logger.error("Unable to determine the name of the new partition!")
            self.logger.error(
                "Disks before partitioning: %s, disks after partitioning: %s, diff: %s",
                old_disks_and_parts, new_disks_and_parts, diff
            )
            return
        return diff[0]

    def create_db_lvm(self, size=5):
        """
        Set up a partition for the CFME DB to run on.

        Args:
            size (int) -- size in GB for the LVM

        Returns:
            True if it worked
            False if it failed

        As a work-around for having to provide a separate disk to a CFME appliance
        for the database, we instead partition the single disk we have and run
        the DB on the new partition.

        This requires that the appliance's disk has more space than CFME requires.
        For example, on RHOS, downstream CFME uses 43GB on a disk but the flavor used
        to deploy the template has a 75GB disk. Therefore, we have extra space which
        we can partition.

        Note that this is not the 'ideal' way of doing things and should
        be a stop-gap measure until we are capabale of attaching additional disks to
        an appliance via automation on all infra types.
        """
        self.logger.info("Creating LVM for DB")

        partition = self._create_partition_from_free_space(size)
        if not partition:
            self.logger.error("Error creating partition, aborting LVM create")
            return False

        fstab_line = '/dev/mapper/dbvg-dblv $APPLIANCE_PG_MOUNT_POINT xfs defaults 0 0'
        commands_to_run = [
            'pvcreate {}'.format(partition),
            'vgcreate dbvg {}'.format(partition),
            'lvcreate --yes -n dblv --size {}G dbvg'.format(size),
            'mkfs.xfs /dev/dbvg/dblv',
            'echo -e "{}" >> /etc/fstab'.format(fstab_line),
            'mount -a'
        ]

        # Permissions modification for upstream or 5.11+
        if not self.appliance.is_downstream or self.appliance.version >= '5.11':
            commands_to_run.extend([
                'chown postgres:postgres $APPLIANCE_PG_MOUNT_POINT',
                'chmod 700 $APPLIANCE_PG_MOUNT_POINT'
            ])

        for command in commands_to_run:
            result = self._run_cmd_show_output(command)
            if result.failed:
                self.logger.error("Command failed! Aborting LVM setup")
                return False
        return True

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
        self.address = self.appliance.hostname
        clear_property_cache(self, 'client')

        client = self.ssh_client

        # Defaults
        db_password = db_password or conf.credentials['database']['password']
        ssh_password = ssh_password or conf.credentials['ssh']['password']

        if not db_disk:
            # See if there's any unpartitioned disks on the appliance
            try:
                db_disk = self.appliance.unpartitioned_disks[0]
                self.logger.info("Using unpartitioned disk for DB at %s", db_disk)
            except IndexError:
                db_disk = None

        db_mounted = False
        if not db_disk:
            # If we still don't have a db disk to use, see if a db disk/partition has already
            # been created & mounted (such as by us in self.create_db_lvm)
            result = client.run_command("mount | grep $APPLIANCE_PG_MOUNT_POINT | cut -f1 -d' '")
            if "".join(str(result).split()):  # strip all whitespace to see if we got a real result
                self.logger.info("Using pre-mounted DB disk at %s", result)
                db_mounted = True

        if not db_mounted and not db_disk:
            self.logger.warning('Failed to find a mounted DB disk, or a free unpartitioned disk.')

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
                # make sure the dbdisk is unmounted, RHOS ephemeral disks come up mounted
                result = client.run_command('umount {}'.format(db_disk))
                if not result.success:
                    self.logger.warning('umount non-zero return, output was: '.format(result))
                command_options = ' '.join([command_options, '--dbdisk {}'.format(db_disk)])

            result = client.run_command(' '.join([base_command, command_options]))
            if result.failed or 'failed' in result.output.lower():
                raise Exception('Could not set up the database:\n{}'.format(result.output))
        else:
            # no cli, use the enable internal db script
            rbt_repl = {
                'miq_lib': '/var/www/miq/lib',
                'region': region,
                'postgres_svcname': self.service_name,
                'postgres_prefix': self.pg_prefix,
                'db_mounted': str(db_mounted),
            }

            # Find and load our rb template with replacements
            rbt = datafile.data_path_for_filename('enable-internal-db.rbt', scripts_path.strpath)
            rb = datafile.load_data_file(rbt, rbt_repl)

            # sent rb file over to /tmp
            remote_file = '/tmp/{}'.format(fauxfactory.gen_alphanumeric())
            client.put_file(rb.name, remote_file)

            # Run the rb script, clean it up when done
            result = client.run_command('ruby {}'.format(remote_file))
            client.run_command('rm {}'.format(remote_file))

        self.logger.info('Output from appliance db configuration: %s', result.output)

        return result.rc, result.output

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

            if not client.is_pod:
                # copy v2 key
                master_client = client(hostname=self.address)
                rand_filename = "/tmp/v2_key_{}".format(fauxfactory.gen_alphanumeric())
                master_client.get_file("/var/www/miq/vmdb/certs/v2_key", rand_filename)
                client.put_file(rand_filename, "/var/www/miq/vmdb/certs/v2_key")

            # enable external DB with cli
            result = client.run_command(
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
            result = client.run_command('ruby {}'.format(remote_file))
            client.run_command('rm {}'.format(remote_file))

        if result.failed:
            self.logger.error('error enabling external db')
            self.logger.error(result.output)
            msg = ('Appliance {} failed to enable external DB running on {}'
                  .format(self.appliance.hostname, db_address))
            self.logger.error(msg)
            from cfme.utils.appliance import ApplianceException
            raise ApplianceException(msg)

        return result.rc, result.output

    @property
    def is_dedicated_active(self):
        return self.appliance.db_service.is_active

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
        return self.address is not None

    @property
    def is_internal(self):
        """Is database internal"""
        return self.address == self.appliance.hostname

    @property
    def is_ready(self):
        """Is database ready"""
        # Using 'and' chain instead of all(...) to
        # prevent calling more things after a step fails
        return self.is_online and self.has_database and self.has_tables

    @property
    def is_online(self):
        """Is database online"""
        db_check_command = ('env PGPASSWORD={pwd} psql -U {user} '
                            '-h {ip} -t  -c "select now()" postgres')
        ensure_host = True if self.ssh_client.is_pod else False
        db_check_command = db_check_command.format(ip=self.address,
                                                   user=conf.credentials['database']['username'],
                                                   pwd=conf.credentials['database']['password'])
        result = self.ssh_client.run_command(db_check_command, ensure_host=ensure_host)
        return result.success

    @property
    def has_database(self):
        """Does database have a database defined"""
        db_check_command = ('env PGPASSWORD={pwd} psql -U {user} -t -h {ip} -c '
                            '"SELECT datname FROM pg_database '
                            'WHERE datname LIKE \'vmdb_%\';" postgres | grep -q vmdb_production')
        ensure_host = True if self.ssh_client.is_pod else False
        db_check_command = db_check_command.format(ip=self.address,
                                                   user=conf.credentials['database']['username'],
                                                   pwd=conf.credentials['database']['password'])
        result = self.ssh_client.run_command(db_check_command, ensure_host=ensure_host)
        return result.success

    @property
    def has_tables(self):
        """Does database have tables defined"""
        db_check_command = ('env PGPASSWORD={pwd} psql -U {user} -t -h {ip} -c "SELECT * FROM '
                            'information_schema.tables WHERE table_schema = \'public\';" '
                            'vmdb_production | grep -q vmdb_production')
        ensure_host = True if self.ssh_client.is_pod else False
        db_check_command = db_check_command.format(ip=self.address,
                                                   user=conf.credentials['database']['username'],
                                                   pwd=conf.credentials['database']['password'])
        result = self.ssh_client.run_command(db_check_command, ensure_host=ensure_host)
        return result.success

    def restore_database(self, db_path, is_major=False):
        """Restore a database on the appliance.

        Args:
            db_path (str): Path to the database. It is required that the database
                            must already be present in the appliance.
            is_major (bool): True if the database belongs to appliance version X
                            and it is to be restored on appliance version Y
                            False if the database belongs to appliance version X
                            and it is to be restored on appliance version X
        """
        self.appliance.evmserverd.stop()
        self.drop()
        self.create()
        self.restore(database_path=db_path)
        self.fix_auth_key()
        if is_major:
            self.migrate()
            self.automate_reset()
        self.appliance.evmserverd.start()
        self.appliance.wait_for_web_ui(timeout=600)
        self.reset_user_pass()
        # need to refresh the appliance
        delattr(self.appliance, "rest_api")
