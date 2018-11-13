import re
from paramiko_expect import SSHClientInteraction

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
        self.ctx.interaction.send(str(self.key))

    def menu_step(self):
        pass

    def __call__(self, *args, **kwargs):
        self.pre_menu_step()
        self.menu_step(*args, **kwargs)
        return self


class AdvancedSettings(ACNav):
    def init_options(self):
        self.configure_network = NetworkConfiguration(self.ctx, 1)
        self.set_timezone = SetTimezone(self.ctx, 2)
        if self.ctx.appliance.version < '5.10':
            self.create_database_backup = CreateDatabaseBackup(self.ctx, 4)

    def menu_step(self):
        self.ctx.interaction.send('')
        self.ctx.interaction.expect('Choose the advanced setting: ')


class NetworkConfiguration(ACNav):
    def init_options(self):
        self.set_dhcp_network_configuration = DHCPNetworkConfiguration(self.ctx, 1)
        self.set_hostname = SetHostname(self.ctx, 5)

    def menu_step(self):
        self.ctx.interaction.expect('Choose the network configuration: ')


class DHCPNetworkConfiguration(ACNav):
    def menu_step(self, enable_ipv4_dhcp, enable_ipv6_dhcp):
        self.ctx.interaction.expect(r'Enable DHCP for IPv4 network configuration\? \(Y/N\): ')
        self.ctx.interaction.send('Y' if enable_ipv4_dhcp else 'N')
        self.ctx.interaction.expect(r'Enable DHCP for IPv6 network configuration\? \(Y/N\): ')
        self.ctx.interaction.send('Y' if enable_ipv6_dhcp else 'N')


class SetHostname(ACNav):
    def menu_step(self, hostname):
        self.ctx.interaction.expect('Enter the new hostname: |.*|')
        self.ctx.interaction.send(hostname)


class CreateDatabaseBackup(ACNav):
    def menu_step(self, storage_system):
        self.ctx.interaction.expect('Choose the backup output storage system: |1|')
        self.ctx.interaction.send(storage_system)


class SetTimezone(ACNav):
    def menu_step(self, options):
        self.ctx.interaction.expect('Choose the geographic location: ')
        for option in options:
            self.ctx.interaction.send(str(option))
            self.ctx.interaction.expect('.*')
        # Answer to 'Change the timezone to .*'
        self.ctx.interaction.send('Y')


class ConfigureDatabase(ACNav):
    def init_options(self):
        self.set_dhcp_network_configuration = DHCPNetworkConfiguration(self.ctx, 1)
        self.set_hostname = SetHostname(self.ctx, 5)

    def menu_step(self):
        self.ctx.interaction.expect('Choose the database operation: ')


class CreateInternalDatabase(ACNav):
    def menu_step(self, disk_option):
        self.ctx.interaction.expect('Choose the database disk: |1|')
        self.ctx.interaction.send(str(disk_option))


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
        self.ctx.interaction.expect('Press any key to continue.', timeout=60)

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
