import re
import logging

from paramiko_expect import SSHClientInteraction


logger = logging.getLogger('cfme.application_console')


def yorn(sel):
    return ('Y' if sel else 'N')


class NavContext(object):
    def __init__(self, appliance):
        self.appliance = appliance
        self.interaction = None


class ACNav(object):
    def __init__(self, ctx, key):
        self.ctx = ctx
        self.key = key
        self.init_options()

    def init_options(self):
        pass

    def pre_menu_step(self):
        self.send(self.key)

    def menu_step(self):
        pass

    def __call__(self, *args, **kwargs):
        self.pre_menu_step()
        self.menu_step(*args, **kwargs)
        return self

    def expect(self, what, timeout=None):
        logger.info('Expecting %s', what)
        if timeout is None:
            self.ctx.interaction.expect(what)
        else:
            self.ctx.interaction.expect(what, timeout)

    def send(self, what):
        logger.info('Sending %s', what)
        self.ctx.interaction.send(str(what))


class AdvancedSettings(ACNav):
    def init_options(self):
        self.configure_network = NetworkConfiguration(self.ctx, 1)
        self.set_timezone = SetTimezone(self.ctx, 2)
        if self.ctx.appliance.version < '5.10':
            self.configure_database_without_key = ConfigureDatabaseWithoutKey(self.ctx, 5)
            self.configure_database_with_key = ConfigureDatabaseWithKey(self.ctx, 5)
        else:
            self.create_database_backup = CreateDatabaseBackup(self.ctx, 4)
            self.create_database_dump = CreateDatabaseDump(self.ctx, 5)
            self.logfile_configuration = LogfileConfiguration(self.ctx, 6)
            self.configure_database_without_key = ConfigureDatabaseWithoutKey(self.ctx, 7)
            self.configure_database_with_key = ConfigureDatabaseWithKey(self.ctx, 7)


    def menu_step(self):
        self.send('')
        self.expect('Choose the advanced setting: ')


class NetworkConfiguration(ACNav):
    def init_options(self):
        self.set_dhcp_network_configuration = DHCPNetworkConfiguration(self.ctx, 1)
        self.set_hostname = SetHostname(self.ctx, 5)

    def menu_step(self):
        self.expect('Choose the network configuration: ')


class DHCPNetworkConfiguration(ACNav):
    def menu_step(self, enable_ipv4_dhcp, enable_ipv6_dhcp):
        self.expect(r'Enable DHCP for IPv4 network configuration\? \(Y/N\): ')
        self.send(yorn(enable_ipv4_dhcp))
        self.expect(r'Enable DHCP for IPv6 network configuration\? \(Y/N\): ')
        self.send(yorn(enable_ipv6_dhcp))


class SetHostname(ACNav):
    def menu_step(self, hostname):
        self.expect('Enter the new hostname: |.*|')
        self.send(hostname)


class CreateDatabaseBackup(ACNav):
    def menu_step(self, storage_system):
        self.expect('Choose the backup output storage system: |1|')
        self.send(storage_system)


class CreateDatabaseDump(ACNav):
    def menu_step(self, storage_system):
        raise NotImplementedError()


class SetTimezone(ACNav):
    def menu_step(self, options):
        self.expect('Choose the geographic location: ')
        for option in options:
            self.send(option)
            self.expect('.*')
        # Answer to 'Change the timezone to .*'
        self.send('Y')


class LogfileConfiguration(ACNav):
    def menu_step(self, storage_system):
        raise NotImplementedError()


class ConfigureDatabaseWithKey(ACNav):
    def init_options(self):
        self.create_internal_database = CreateInternalDatabase(self.ctx, 1)
        self.create_region_in_external_db = CreateRegionInExternalDatabase(self.ctx, 2)
        self.join_region_in_external_db = JoinRegionInExternalDatabase(self.ctx, 3)
        self.reset_configured_db = ResetConfiguredDatabase(self.ctx, 4)

    def menu_step(self):
        self.expect('Choose the database operation: ')


class ConfigureDatabaseWithoutKey(ACNav):
    def init_options(self):
        self.create_key = ConfigureDatabaseWithKey(self.ctx, 1)
        self.fetch_key_from_remote_machine = FetchKeyFromRemoteMachine(self.ctx, 2)

    def menu_step(self):
        self.expect('Choose the encryption key: |1| ')


class FetchKeyFromRemoteMachine(ACNav):
    def menu_step(self, storage_system):
        raise NotImplementedError()


class CreateInternalDatabase(ACNav):
    def menu_step(self, disk_option, standalone, region, db_pass):
        self.expect('Choose the database disk: |1|')
        self.send(disk_option)
        self.expect(
            'Should this appliance run as a standalone database server\?.*'
            '\(Y\/N\): |N| ')
        self.send(yorn(standalone))
        self.expect('Enter the database region number: ')
        self.send(region)
        self.expect('Enter the database password on localhost: ')
        self.send(db_pass)
        self.expect('Enter the database password again: ')
        self.send(db_pass)
        self.expect('Create region complete.*'
                    'Configuration activated successfully\..*'
                    'Press any key to continue.', timeout=60)
        self.send('')

class CreateRegionInExternalDatabase(ACNav):
    def menu_step(self, storage_system):
        raise NotImplementedError()


class JoinRegionInExternalDatabase(ACNav):
    def menu_step(self, storage_system):
        raise NotImplementedError()


class ResetConfiguredDatabase(ACNav):
    def menu_step(self, storage_system):
        raise NotImplementedError()




class ApplianceConsole(ACNav):
    """ApplianceConsole is used for navigating and running appliance_console commands against an
    appliance."""

    def __init__(self, appliance):
        self.appliance = appliance
        ACNav.__init__(self, NavContext(appliance), 'ap')
        self.advanced_settings = AdvancedSettings(self.ctx, '')

    def pre_menu_step(self):
        interaction = SSHClientInteraction(self.ctx.appliance.ssh_client,
                                           timeout=10, display=True)
        self.ctx.interaction = interaction
        super(ApplianceConsole, self).pre_menu_step()

    def menu_step(self):
        self.expect('Press any key to continue.', timeout=60)

    def timezone_check(self, timezone):
        ia = self.ctx.interaction
        m = re.search('Timezone: *(.*)$', ia.current_output, re.MULTILINE)
        assert m.group(1) == timezone

    def run_commands(self, commands, autoreturn=True, timeout=10, channel=None):
        if not channel:
            channel = self.appliance.ssh_client.invoke_shell()
        self.commands = commands
        for command in commands:
            if isinstance(command, six.string_types):
                command_string, timeout = command, timeout
            else:
                command_string, timeout = command
            channel.settimeout(timeout)
            if autoreturn:
                command_string = (command_string + '\n')
            channel.send("{}".format(command_string))
            result = ''
            try:
                while True:
                    result += channel.recv(1)
                    if 'Press any key to continue' in result:
                        break
            except socket.timeout:
                pass
            logger.debug(result)

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
            yml = yaml.load(f.read())
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
