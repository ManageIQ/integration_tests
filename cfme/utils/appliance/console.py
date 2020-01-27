import os
import socket
import tempfile
from contextlib import contextmanager
from re import escape as resc

import lxml
import yaml

from cfme.utils.appliance.plugin import AppliancePlugin
from cfme.utils.conf import hidden
from cfme.utils.log import logger
from cfme.utils.log_validator import LogValidator
from cfme.utils.ssh_expect import SSHExpect
from cfme.utils.wait import wait_for


class ApplianceConsole(AppliancePlugin):
    """ApplianceConsole is used for navigating and running appliance_console commands against an
    appliance."""

    def timezone_check(self, timezone):
        channel = self.appliance.ssh_client.invoke_shell()
        channel.settimeout(20)
        channel.send("ap")
        result = ''
        try:
            while True:
                result += str(channel.recv(1))
                if ("{}".format(timezone[0])) in result:
                    break
        except socket.timeout:
            pass
        logger.debug(result)

    def run_commands(self, commands, autoreturn=True, timeout=10, channel=None, output=False):
        stdout = []
        if not channel:
            channel = self.appliance.ssh_client.invoke_shell()
        self.commands = commands
        for command in commands:
            if isinstance(command, str):
                cmd, timeout = command, timeout
            else:
                cmd, timeout = command
            channel.settimeout(timeout)
            cmd = "{}\n".format(cmd) if autoreturn else "{}".format(cmd)
            logger.info("Executing sub-command: %s" % cmd)
            channel.send(cmd)
            result = ''
            try:
                while True:
                    result += channel.recv(1).decode("ascii")
                    if "Press any key to continue" in result or channel.closed:
                        break
            except socket.timeout:
                logger.warning("socket.timeout exception raised for command: %s, "
                               "timeout value: %s" % (cmd, timeout))
            stdout.append(result)
            logger.debug(result)
        if output:
            logger.info("commands output: %s" % result)
            return stdout

    def scap_harden_appliance(self):
        """Commands:
        1. 'ap' launches appliance_console,
        2. '' clears info screen,
        3. '14' Hardens appliance using SCAP configuration,
        4. '' complete."""
        command_set = ('ap', '', '13', '')
        self.appliance.appliance_console.run_commands(command_set)

    def scap_check_rules(self):
        """Check that rules have been applied correctly."""
        rules_failures = []
        with tempfile.NamedTemporaryFile('w') as f:
            f.write(hidden['scap.rb'])
            f.flush()
            os.fsync(f.fileno())
            self.appliance.ssh_client.put_file(
                f.name, '/tmp/scap.rb')
        if self.appliance.version >= "5.8":
            rules = '/var/www/miq/vmdb/productization/appliance_console/config/scap_rules.yml'
        else:
            rules = '/var/www/miq/vmdb/gems/pending/appliance_console/config/scap_rules.yml'
        self.appliance.ssh_client.run_command(
            'cd /tmp/ && ruby scap.rb --rulesfile={rules}'.format(rules=rules))
        self.appliance.ssh_client.get_file(
            '/tmp/scap-results.xccdf.xml', '/tmp/scap-results.xccdf.xml')
        self.appliance.ssh_client.get_file(
            '{rules}'.format(rules=rules), '/tmp/scap_rules.yml')  # Get the scap rules

        with open('/tmp/scap_rules.yml') as f:
            yml = yaml.safe_load(f.read())
            rules = yml['rules']

        tree = lxml.etree.parse('/tmp/scap-results.xccdf.xml')
        root = tree.getroot()
        for rule in rules:
            elements = root.findall(
                './/{{http://checklists.nist.gov/xccdf/1.1}}rule-result[@idref="{}"]'.format(rule))
            if elements:
                result = elements[0].findall('./{http://checklists.nist.gov/xccdf/1.1}result')
                if result:
                    if result[0].text != 'pass':
                        rules_failures.append(rule)
                    logger.info("{}: {}".format(rule, result[0].text))
                else:
                    logger.info("{}: no result".format(rule))
            else:
                logger.info("{}: rule not found".format(rule))
        return rules_failures

    def configure_primary_replication_node(self, pwd):
        # Configure primary replication node
        with SSHExpect(self.appliance) as interaction:
            interaction.send('ap')
            interaction.answer('Press any key to continue.', '', timeout=20)
            # 6/8 for Configure Database Replication
            interaction.answer('Choose the advanced setting: ',
                               '6' if self.appliance.version < '5.10' else '8')
            interaction.answer('Choose the database replication operation: ', '1')
            answer_cluster_related_questions(interaction, node_uid='1',
                db_name='', db_username='', db_password=pwd)
            interaction.answer(r'Enter the primary database hostname or IP address: \|.*\| ',
                               self.appliance.hostname)
            interaction.answer(resc('Apply this Replication Server Configuration? (Y/N): '), 'y')
            interaction.answer('Press any key to continue.', '')

    def reconfigure_primary_replication_node(self, pwd):
        # Configure primary replication node
        with SSHExpect(self.appliance) as interaction:
            interaction.send('ap')
            interaction.answer('Press any key to continue.', '', timeout=20)
            interaction.answer('Choose the advanced setting: ',
                               '6' if self.appliance.version < '5.10' else '8')
            # 6/8 for Configure Database Replication

            interaction.answer('Choose the database replication operation: ', '1')
            answer_cluster_related_questions(interaction, node_uid='1',
                db_name='', db_username='', db_password=pwd)
            interaction.answer(r'Enter the primary database hostname or IP address: \|.*\| ',
                               self.appliance.hostname)
            # Warning: File /etc/repmgr.conf exists. Replication is already configured
            interaction.answer(resc('Continue with configuration? (Y/N): '), 'y')
            interaction.answer(resc('Apply this Replication Server Configuration? (Y/N): '), 'y')
            interaction.answer('Press any key to continue.', '')

    def configure_standby_replication_node(self, pwd, primary_ip):
        # Configure secondary (standby) replication node
        with SSHExpect(self.appliance) as interaction:
            interaction.send('ap')
            interaction.answer('Press any key to continue.', '', timeout=20)
            interaction.answer('Choose the advanced setting: ',
                               '6' if self.appliance.version < '5.10' else '8')
            # 6/8 for Configure Database Replication

            # Configure Server as Standby
            interaction.answer('Choose the database replication operation: ', '2')
            interaction.answer(resc('Choose the encryption key: |1| '), '2')
            interaction.send(primary_ip)
            interaction.answer(resc('Enter the appliance SSH login: |root| '), '')
            interaction.answer('Enter the appliance SSH password: ', pwd)
            interaction.answer(resc('Enter the path of remote encryption key: '
                                    '|/var/www/miq/vmdb/certs/v2_key| '), '')
            interaction.answer(resc('Choose the standby database disk: '),
                               '1' if self.appliance.version < '5.10' else '2')
            answer_cluster_related_questions(interaction, node_uid='2',
                db_name='', db_username='', db_password=pwd)
            interaction.answer('Enter the primary database hostname or IP address: ', primary_ip)
            interaction.answer(r'Enter the Standby Server hostname or IP address: \|.*\| ',
                               self.appliance.hostname)
            interaction.answer(resc('Configure Replication Manager (repmgrd) for automatic '
                                    r'failover? (Y/N): '), 'y')
            interaction.answer(resc('Apply this Replication Server Configuration? (Y/N): '), 'y')
            interaction.answer('Press any key to continue.', '', timeout=10 * 60)

    def reconfigure_standby_replication_node(self, pwd, primary_ip, repmgr_reconfigure=False):
        # Configure secondary (standby) replication node
        with SSHExpect(self.appliance) as interaction:
            interaction.send('ap')
            # When reconfiguring, the ap command may hang for 60s even.
            interaction.answer('Press any key to continue.', '', timeout=120)
            interaction.answer('Choose the advanced setting: ',
                               '6' if self.appliance.version < '5.10' else '8')
            # 6/8 for Configure Database Replication

            # Configure Server as Standby
            interaction.answer('Choose the database replication operation: ', '2')
            # Would you like to remove the existing database before configuring as a standby server?
            # WARNING: This is destructive. This will remove all previous data from this server
            interaction.answer(resc('Continue? (Y/N): '), 'y')
            interaction.answer(
                # Don't partition the disk
                resc('Choose the standby database disk: |1| '),
                '1' if self.appliance.version < '5.10' else '2')
            interaction.answer(resc(
                "Are you sure you don't want to partition the Standby "
                "database disk? (Y/N): "), 'y')
            answer_cluster_related_questions(interaction, node_uid='2',
                db_name='', db_username='', db_password=pwd)
            interaction.answer('Enter the primary database hostname or IP address: ', primary_ip)
            interaction.answer(r'Enter the Standby Server hostname or IP address: \|.*\| ', '')
            interaction.answer(resc(
                'Configure Replication Manager (repmgrd) for automatic '
                r'failover? (Y/N): '), 'y')
            # interaction.answer('An active standby node (10.8.198.223) with the node number 2
            # already exists\n')
            # 'Would you like to continue configuration by overwriting '
            # 'the existing node?
            interaction.answer(resc('(Y/N): |N| '), 'y')
            # Warning: File /etc/repmgr.conf exists. Replication is already configured
            interaction.answer(resc('Continue with configuration? (Y/N): '), 'y')
            interaction.answer(resc('Apply this Replication Server Configuration? (Y/N): '), 'y')
            interaction.answer('Press any key to continue.', '', timeout=20)

    def configure_automatic_failover(self, primary_ip):
        # Configure automatic failover on EVM appliance
        with SSHExpect(self.appliance) as interaction:
            interaction.send('ap')
            interaction.answer('Press any key to continue.', '', timeout=20)
            interaction.expect('Choose the advanced setting: ')

            with waiting_for_ha_monitor_started(self.appliance, primary_ip, timeout=300):
                # Configure Application Database Failover Monitor
                interaction.send('8' if self.appliance.version < '5.10' else '10')
                interaction.answer('Choose the failover monitor configuration: ', '1')
                # Failover Monitor Service configured successfully
                interaction.answer('Press any key to continue.', '')


@contextmanager
def waiting_for_ha_monitor_started(appl, standby_server_ip, timeout):
    if appl.version < '5.10':
        with LogValidator(
                "/var/www/miq/vmdb/config/failover_databases.yml",
                matched_patterns=[standby_server_ip],
                hostname=appl.hostname).waiting(timeout=timeout):
            yield
    else:
        yield
        wait_for(lambda: appl.evm_failover_monitor.running, timeout=300)


def configure_appliances_ha(appliances, pwd):
    """Configure HA environment

    Appliance one configuring dedicated database, 'ap' launch appliance_console,
    '' clear info screen, '5' setup db, '1' Creates v2_key, '1' selects internal db,
    '1' use partition, 'y' create dedicated db, 'pwd' db password, 'pwd' confirm db password + wait
    and '' finish.

    Appliance two creating region in dedicated database, 'ap' launch appliance_console, '' clear
    info screen, '5' setup db, '2' fetch v2_key, 'app0_ip' appliance ip address, '' default user,
    'pwd' appliance password, '' default v2_key location, '2' create region in external db, '0' db
    region number, 'y' confirm create region in external db 'app0_ip', '' ip and default port for
    dedicated db, '' use default db name, '' default username, 'pwd' db password, 'pwd' confirm db
    password + wait and '' finish.

    Appliance one configuring primary node for replication, 'ap' launch appliance_console, '' clear
    info screen, '6' configure db replication, '1' configure node as primary, '1' cluster node
    number set to 1, '' default dbname, '' default user, 'pwd' password, 'pwd' confirm password,
    'app0_ip' primary appliance ip, confirm settings and wait to configure, '' finish.


    Appliance three configuring standby node for replication, 'ap' launch appliance_console, ''
    clear info screen, '6' configure db replication, '2' configure node as standby, '2' cluster node
    number set to 2, '' default dbname, '' default user, 'pwd' password, 'pwd' confirm password,
    'app0_ip' primary appliance ip, app1_ip standby appliance ip, confirm settings and wait
    to configure finish, '' finish.


    Appliance two configuring automatic failover of database nodes, 'ap' launch appliance_console,
    '' clear info screen '9' configure application database failover monitor, '1' start failover
    monitor. wait 30 seconds for service to start '' finish.

    """
    apps0, apps1, apps2 = appliances
    app0_ip = apps0.hostname

    # Configure first appliance as dedicated database
    with SSHExpect(apps0) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=20)
        interaction.answer('Choose the advanced setting: ',
                           '5' if apps0.version < '5.10' else '7')  # Configure Database
        interaction.answer(resc('Choose the encryption key: |1| '), '1')
        interaction.answer('Choose the database operation: ', '1')
        # On 5.10, rhevm provider:
        #
        #    database disk
        #
        #    1) /dev/sr0: 0 MB
        #    2) /dev/vdb: 4768 MB
        #    3) Don't partition the disk
        interaction.answer(resc('Choose the database disk: '),
                          '1' if apps0.version < '5.10' else '2')
        # Should this appliance run as a standalone database server?
        interaction.answer(resc('? (Y/N): |N| '), 'y')
        interaction.answer('Enter the database password on localhost: ', pwd)
        interaction.answer('Enter the database password again: ', pwd)
        # Configuration activated successfully.
        interaction.answer('Press any key to continue.', '', timeout=6 * 60)

        wait_for(lambda: apps0.db.is_dedicated_active, num_sec=4 * 60)

    # Configure EVM webui appliance with create region in dedicated database
    with SSHExpect(apps2) as interaction:
        interaction.send('ap')
        interaction.answer('Press any key to continue.', '', timeout=20)
        interaction.answer('Choose the advanced setting: ',
                           '5' if apps2.version < '5.10' else '7')  # Configure Database
        interaction.answer(resc('Choose the encryption key: |1| '), '2')
        interaction.send(app0_ip)
        interaction.answer(resc('Enter the appliance SSH login: |root| '), '')
        interaction.answer('Enter the appliance SSH password: ', pwd)
        interaction.answer(
            resc('Enter the path of remote encryption key: |/var/www/miq/vmdb/certs/v2_key| '),
            '')
        interaction.answer('Choose the database operation: ', '2', timeout=30)
        interaction.answer('Enter the database region number: ', '0')
        # WARNING: Creating a database region will destroy any existing data and
        # cannot be undone.
        interaction.answer(resc('Are you sure you want to continue? (Y/N):'), 'y')
        interaction.answer('Enter the database hostname or IP address: ', app0_ip)
        interaction.answer(resc('Enter the port number: |5432| '), '')
        interaction.answer(r'Enter the name of the database on .*: \|vmdb_production\| ', '')
        interaction.answer(resc('Enter the username: |root| '), '')
        interaction.answer('Enter the database password on .*: ', pwd)
        # Configuration activated successfully.
        interaction.answer('Press any key to continue.', '', timeout=360)

    apps2.evmserverd.wait_for_running()
    apps2.wait_for_web_ui()

    apps0.appliance_console.configure_primary_replication_node(pwd)
    apps1.appliance_console.configure_standby_replication_node(pwd, app0_ip)

    apps2.appliance_console.configure_automatic_failover(primary_ip=None)
    return appliances


def answer_cluster_related_questions(interaction, node_uid, db_name,
        db_username, db_password):
    # It seems like sometimes, the word "Enter " ... dosen't fit to the paramiko-expect buffer.
    # This seems to happen when (re)configuring the standby replication node.
    interaction.answer('.* the number uniquely identifying '
                       'this node in the replication cluster: ', node_uid)
    interaction.answer(resc('Enter the cluster database name: |vmdb_production| '), db_name)
    interaction.answer(resc('Enter the cluster database username: |root| '), db_username)
    interaction.answer('Enter the cluster database password: ', db_password)
    interaction.answer('Enter the cluster database password: ', db_password)


class ApplianceConsoleCli(AppliancePlugin):
    def _run(self, appliance_console_cli_command, timeout=35):
        result = self.appliance.ssh_client.run_command(
            "appliance_console_cli {}".format(appliance_console_cli_command),
            timeout)
        return result

    def set_hostname(self, hostname):
        return self._run("--host {host}".format(host=hostname), timeout=60)

    def configure_appliance_external_join(self, dbhostname,
            username, password, dbname, fetch_key, sshlogin, sshpass):
        self._run("--hostname {dbhostname} --username {username} --password {password}"
            " --dbname {dbname} --verbose --fetch-key {fetch_key} --sshlogin {sshlogin}"
            " --sshpassword {sshpass}".format(dbhostname=dbhostname, username=username,
                password=password, dbname=dbname, fetch_key=fetch_key, sshlogin=sshlogin,
                sshpass=sshpass), timeout=300)

    def configure_appliance_external_create(self, region, dbhostname,
            username, password, dbname, fetch_key, sshlogin, sshpass):
        self._run("--region {region} --hostname {dbhostname} --username {username}"
            " --password {password} --dbname {dbname} --verbose --fetch-key {fetch_key}"
            " --sshlogin {sshlogin} --sshpassword {sshpass}".format(
                region=region, dbhostname=dbhostname, username=username, password=password,
                dbname=dbname, fetch_key=fetch_key, sshlogin=sshlogin, sshpass=sshpass),
            timeout=300)

    def configure_appliance_internal(self, region, dbhostname, username, password, dbname, dbdisk):
        self._run("--region {region} --internal --hostname {dbhostname} --username {username}"
            " --password {password} --dbname {dbname} --verbose --dbdisk {dbdisk}".format(
                region=region, dbhostname=dbhostname, username=username, password=password,
                dbname=dbname, dbdisk=dbdisk), timeout=5 * 60)

    def configure_appliance_internal_fetch_key(self, region, dbhostname,
            username, password, dbname, dbdisk, fetch_key, sshlogin, sshpass):
        self._run("--region {region} --internal --hostname {dbhostname} --username {username}"
            " --password {password} --dbname {dbname} --verbose --dbdisk {dbdisk} --fetch-key"
            " {fetch_key} --sshlogin {sshlogin} --sshpassword {sshpass}".format(
                region=region, dbhostname=dbhostname, username=username, password=password,
                dbname=dbname, dbdisk=dbdisk, fetch_key=fetch_key, sshlogin=sshlogin,
                sshpass=sshpass), timeout=600)

    def configure_appliance_dedicated_db(self, username, password, dbname, dbdisk):
        self._run("--internal --username {username} --password {password}"
            " --dbname {dbname} --verbose --dbdisk {dbdisk} --key --standalone".format(
                username=username, password=password, dbname=dbname, dbdisk=dbdisk), timeout=300)

    def configure_ipa(self, ipaserver, ipaprincipal, ipapassword, ipadomain=None, iparealm=None):
        cmd_result = self._run(
            '--ipaserver {s} --ipaprincipal {u} --ipapassword {p} {d} {r}'
            .format(s=ipaserver, u=ipaprincipal, p=ipapassword,
                    d='--ipadomain {}'.format(ipadomain) if ipadomain else '',
                    r='--iparealm {}'.format(iparealm) if iparealm else ''), timeout=90)
        logger.debug('IPA configuration output: %s', str(cmd_result))
        assert cmd_result.success
        assert 'ipa-client-install exit code: 1' not in cmd_result.output
        self.appliance.sssd.wait_for_running()
        assert self.appliance.ssh_client.run_command("cat /etc/ipa/default.conf "
                                                     "| grep 'enable_ra = True'")

    def configure_appliance_dedicated_ha_primary(
            self, username, password, reptype, primhost, node, dbname):
        self._run("--username {username} --password {password} --replication {reptype}"
            " --primary-host {primhost} --cluster-node-number {node} --auto-failover --verbose"
            " --dbname {dbname}".format(
                username=username, password=password, reptype=reptype, primhost=primhost, node=node,
                dbname=dbname))

    def configure_appliance_dedicated_ha_standby(
            self, username, password, reptype, primhost, standhost, node, dbname, dbdisk):
        self._run("--internal --username {username} --password {password} --replication {reptype}"
            " --primary-host {primhost} --standby-host {standhost} --cluster-node-number {node}"
            " --auto-failover --dbname {dbname} --verbose --dbdisk {dbdisk}"
            " --standalone".format(username=username, password=password, reptype=reptype,
                primhost=primhost, standhost=standhost, node=node, dbname=dbname, dbdisk=dbdisk),
                  timeout=300)

    def uninstall_ipa_client(self):
        assert self._run("--uninstall-ipa", timeout=90)
        assert not self.appliance.ssh_client.run_command("cat /etc/ipa/default.conf")
