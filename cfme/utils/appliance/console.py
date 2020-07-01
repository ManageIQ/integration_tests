import re
import socket

import lxml
import yaml

from cfme.utils.appliance.plugin import AppliancePlugin
from cfme.utils.log import logger
from cfme.utils.path import scripts_path
from cfme.utils.ssh_expect import SSHExpect
from cfme.utils.version import LOWEST
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker

AP_WELCOME_SCREEN_TIMEOUT = 30


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

    def run_commands(self, commands, autoreturn=True, timeout=10, channel=None):
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
            cmd = f"{cmd}\n" if autoreturn else f"{cmd}"
            logger.info(f"Executing sub-command: {cmd}, timeout:{timeout}")
            channel.send(cmd)
            result = ''
            try:
                while True:
                    result += channel.recv(1).decode("ascii", "backslashreplace")
                    if "Press any key to continue" in result or channel.closed:
                        break
            except socket.timeout:
                logger.warning("socket.timeout exception raised for command: %s, "
                               "timeout value: %s" % (cmd, timeout))
            stdout.append(result)
            logger.info("current command's output: %s" % result)
        logger.info("All commands output: %s" % stdout)
        return stdout

    def scap_harden_appliance(self):
        """Commands:
        1. 'ap' launches appliance_console,
        2. '' clears info screen,
        3. '15' Hardens appliance using SCAP configuration,
        4. '' complete."""
        with SSHExpect(self.appliance) as interaction:
            interaction.send('ap')
            interaction.answer('Press any key to continue.', '', timeout=AP_WELCOME_SCREEN_TIMEOUT)
            interaction.answer('Choose the advanced setting: ', VersionPicker({
                LOWEST: 15,
                '5.11.2.1': 13
            }))
            interaction.answer('Press any key to continue.', '', timeout=AP_WELCOME_SCREEN_TIMEOUT)

    def scap_failures(self):
        """Return applied scap rules failure list."""
        rules_failures = []

        self.appliance.ssh_client.put_file(scripts_path.join('scap.rb'), '/tmp/scap.rb')

        if self.appliance.version >= "5.8":
            rules = '/var/www/miq/vmdb/productization/appliance_console/config/scap_rules.yml'
        else:
            rules = '/var/www/miq/vmdb/gems/pending/appliance_console/config/scap_rules.yml'

        ssg_path = VersionPicker({
            Version.lowest(): "/usr/share/xml/scap/ssg/content/ssg-rhel7-ds.xml",
            '5.11': "/usr/share/xml/scap/ssg/content/ssg-rhel8-ds.xml"
        }).pick(self.appliance.version)

        assert self.appliance.ssh_client.run_command('gem install optimist').success
        assert self.appliance.ssh_client.run_command(
            f'cd /tmp/ && ruby scap.rb --rulesfile={rules} --ssg-path={ssg_path}')
        self.appliance.ssh_client.get_file(
            '/tmp/scap-results.xccdf.xml', '/tmp/scap-results.xccdf.xml')
        self.appliance.ssh_client.get_file(
            f'{rules}', '/tmp/scap_rules.yml')  # Get the scap rules

        with open('/tmp/scap_rules.yml') as f:
            yml = yaml.safe_load(f.read())
            rules = yml['rules']

        tree = lxml.etree.parse('/tmp/scap-results.xccdf.xml')
        root = tree.getroot()
        for rule in rules:
            elements = root.findall(
                f'.//{{http://checklists.nist.gov/xccdf/1.1}}rule-result[@idref="{rule}"]')
            if elements:
                result = elements[0].findall('./{http://checklists.nist.gov/xccdf/1.1}result')
                if result:
                    if result[0].text != 'pass':
                        rules_failures.append(rule)
                    logger.info("{}: {}".format(rule, result[0].text))
                else:
                    logger.info(f"{rule}: no result")
            else:
                logger.info(f"{rule}: rule not found")
        return rules_failures

    def configure_primary_replication_node(self, pwd):
        # Configure primary replication node
        with SSHExpect(self.appliance) as interaction:
            interaction.send('ap')
            interaction.answer('Press any key to continue.', '', timeout=AP_WELCOME_SCREEN_TIMEOUT)
            # 6/8 for Configure Database Replication
            interaction.answer('Choose the advanced setting: ', VersionPicker({
                LOWEST: 6,
                '5.10': 8,
                '5.11.2.1': 6
            }))
            interaction.answer('Choose the database replication operation: ', '1')
            answer_cluster_related_questions(interaction, node_uid='1',
                db_name='', db_username='', db_password=pwd)
            interaction.answer(r'Enter the primary database hostname or IP address: \|.*\| ',
                               self.appliance.hostname)
            interaction.answer(
                re.escape('Apply this Replication Server Configuration? (Y/N): '), 'y')
            interaction.answer('Press any key to continue.', '')

    def reconfigure_primary_replication_node(self, pwd):
        # Configure primary replication node
        with SSHExpect(self.appliance) as interaction:
            interaction.send('ap')
            interaction.answer('Press any key to continue.', '', timeout=AP_WELCOME_SCREEN_TIMEOUT)
            interaction.answer('Choose the advanced setting: ', VersionPicker({
                LOWEST: '6',
                '5.10': 8,
                '5.11.2.1': 6
            }))
            # 6/8 for Configure Database Replication

            interaction.answer('Choose the database replication operation: ', '1')
            answer_cluster_related_questions(interaction, node_uid='1',
                db_name='', db_username='', db_password=pwd)
            interaction.answer(r'Enter the primary database hostname or IP address: \|.*\| ',
                               self.appliance.hostname)
            # Warning: File /etc/repmgr.conf exists. Replication is already configured
            interaction.answer(re.escape('Continue with configuration? (Y/N): '), 'y')
            interaction.answer(
                re.escape('Apply this Replication Server Configuration? (Y/N): '), 'y')
            interaction.answer('Press any key to continue.', '')

    def configure_standby_replication_node(self, pwd, primary_ip):
        # Configure secondary (standby) replication node
        with SSHExpect(self.appliance) as interaction:
            interaction.send('ap')
            interaction.answer('Press any key to continue.', '', timeout=AP_WELCOME_SCREEN_TIMEOUT)
            interaction.answer('Choose the advanced setting: ', VersionPicker({
                LOWEST: '6',
                '5.10': 8,
                '5.11.2.1': 6
            }))
            # 6/8 for Configure Database Replication

            # Configure Server as Standby
            interaction.answer('Choose the database replication operation: ', '2')
            interaction.answer(re.escape('Choose the encryption key: |1| '), '2')
            interaction.send(primary_ip)
            interaction.answer(re.escape('Enter the appliance SSH login: |root| '), '')
            interaction.answer('Enter the appliance SSH password: ', pwd)
            interaction.answer(re.escape('Enter the path of remote encryption key: '
                                    '|/var/www/miq/vmdb/certs/v2_key| '), '')
            if self.appliance.version < '5.11.2.0':
                interaction.answer(re.escape('Choose the standby database disk: '),
                                '1' if self.appliance.version < '5.10' else '2')
            else:
                interaction.answer(re.escape('Choose the standby database disk: |1| '), '')
            answer_cluster_related_questions(interaction, node_uid='2',
                db_name='', db_username='', db_password=pwd)
            interaction.answer('Enter the primary database hostname or IP address: ', primary_ip)
            interaction.answer(r'Enter the Standby Server hostname or IP address: \|.*\| ',
                               self.appliance.hostname)
            interaction.answer(re.escape('Configure Replication Manager (repmgrd) for automatic '
                                    r'failover? (Y/N): '), 'y')
            interaction.answer(
                re.escape('Apply this Replication Server Configuration? (Y/N): '), 'y')
            interaction.answer('Press any key to continue.', '', timeout=10 * 60)

    def reconfigure_standby_replication_node(self, pwd, primary_ip, repmgr_reconfigure=False):
        # Configure secondary (standby) replication node
        with SSHExpect(self.appliance) as interaction:
            interaction.send('ap')
            # When reconfiguring, the ap command may hang for 60s even.
            interaction.answer('Press any key to continue.', '', timeout=120)
            interaction.answer('Choose the advanced setting: ', VersionPicker({
                LOWEST: '6',
                '5.10': 8,
                '5.11.2.1': 6
            }))
            # 6/8 for Configure Database Replication

            # Configure Server as Standby
            interaction.answer('Choose the database replication operation: ', '2')
            # Would you like to remove the existing database before configuring as a standby server?
            # WARNING: This is destructive. This will remove all previous data from this server
            interaction.answer(re.escape('Continue? (Y/N): '), 'y')
            if self.appliance.version < '5.11.2.0':
                interaction.answer(
                    # Don't partition the disk
                    re.escape('Choose the standby database disk: |1| '),
                    '1' if self.appliance.version < '5.10' else '2')
            interaction.answer(re.escape(
                "Are you sure you don't want to partition the Standby "
                "database disk? (Y/N): "), 'y')
            answer_cluster_related_questions(interaction, node_uid='2',
                db_name='', db_username='', db_password=pwd)
            interaction.answer('Enter the primary database hostname or IP address: ', primary_ip)
            interaction.answer(r'Enter the Standby Server hostname or IP address: \|.*\| ', '')
            interaction.answer(re.escape(
                'Configure Replication Manager (repmgrd) for automatic '
                r'failover? (Y/N): '), 'y')
            # interaction.answer('An active standby node (10.8.198.223) with the node number 2
            # already exists\n')
            # 'Would you like to continue configuration by overwriting '
            # 'the existing node?
            interaction.answer(re.escape('(Y/N): |N| '), 'y')
            # Warning: File /etc/repmgr.conf exists. Replication is already configured
            interaction.answer(re.escape('Continue with configuration? (Y/N): '), 'y')
            interaction.answer(
                re.escape('Apply this Replication Server Configuration? (Y/N): '), 'y')
            interaction.answer('Press any key to continue.', '', timeout=AP_WELCOME_SCREEN_TIMEOUT)


def answer_cluster_related_questions(interaction, node_uid, db_name,
        db_username, db_password):
    # It seems like sometimes, the word "Enter " ... doesn't fit to the paramiko-expect buffer.
    # This seems to happen when (re)configuring the standby replication node.
    interaction.answer('.* the number uniquely identifying '
                       'this node in the replication cluster: ', node_uid)
    interaction.answer(re.escape('Enter the cluster database name: |vmdb_production| '),
                       db_name)
    interaction.answer(re.escape('Enter the cluster database username: |root| '),
                       db_username)
    interaction.answer('Enter the cluster database password: ', db_password)
    interaction.answer('Enter the cluster database password: ', db_password)


class ApplianceConsoleCli(AppliancePlugin):
    def _run(self, appliance_console_cli_command, timeout=35):
        result = self.appliance.ssh_client.run_command(
            f"appliance_console_cli {appliance_console_cli_command}",
            timeout)
        return result

    def set_hostname(self, hostname):
        return self._run(f"--host {hostname}", timeout=60)

    def configure_appliance_external_join(self, dbhostname,
            username, password, dbname, fetch_key, sshlogin, sshpass):
        self._run("--hostname {dbhostname} --username {username} --password {password}"
            " --dbname {dbname} --verbose --fetch-key {fetch_key} --sshlogin {sshlogin}"
            " --sshpassword {sshpass}".format(dbhostname=dbhostname, username=username,
                password=password, dbname=dbname, fetch_key=fetch_key, sshlogin=sshlogin,
                sshpass=sshpass), timeout=500)

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
                    d=f'--ipadomain {ipadomain}' if ipadomain else '',
                    r=f'--iparealm {iparealm}' if iparealm else ''), timeout=90)
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
