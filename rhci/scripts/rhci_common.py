import time

import sarge
from neutronclient.v2_0.client import Client as Neutron
from novaclient.utils import find_resource
from vncdotool import api as vnc

from utils import browser, conf
from utils.providers import get_mgmt as _get_mgmt
from utils.ssh import SSHClient


def save_rhci_conf(**rhci_conf_updates):
    """Write the current state of the rhci conf out to the conf yaml"""
    conf.rhci.update(rhci_conf_updates)
    conf.save('rhci')
    return conf.rhci


def ssh_client():
    return SSHClient(hostname=conf.rhci.ip_address, stream_output=True)


def get_mgmt():
    return _get_mgmt(conf.rhci.provider_key)


def virsh(args):
    result = sarge.capture_stdout('virsh {}'.format(args))
    if result.returncode != 0:
        raise RuntimeError('virsh command failed with exit code {}'.format(result.returncode))
    return result.stdout.read().strip()


def neutron_client():
    mgmt = get_mgmt()
    return Neutron(username=mgmt.username, password=mgmt.password, tenant_name=mgmt.tenant,
        auth_url=mgmt.auth_url, insecure=True)


def find_best_flavor(nova_api, cpu_count, memory, disk_size, allow_ephemeral=False):
    # get the list of flavors, sorted by ram (lowest first)
    flavors = sorted(nova_api.flavors.list(), key=lambda f: f.ram)

    # filter out flavors with ephemeral volumes, if desired
    if not allow_ephemeral:
        flavors = filter(lambda f: not f.ephemeral, flavors)

    # return the first flavor that has the required amount of cpus, disk space, and memory
    for flavor in flavors:
        # flavor.ram is in MB, memory is GB, so floor div it to match what we expect
        flavor_ram = flavor.ram / 1024
        if all([flavor.vcpus >= cpu_count, flavor_ram >= memory, flavor.disk >= disk_size]):
            return flavor
    else:
        raise RuntimeError('Could not find a flavor suporting '
            '{} CPUs, {} GB RAM, and a {} GB disk'.format(cpu_count, memory, disk_size))


class NoRHCIConfError(Exception):
    def __init__(self):
        msg = 'RHCI config yaml not found or empty'
        super(NoRHCIConfError, self).__init__(msg)


class VNCTyper(object):
    """Helps make manipulating remote desktops via VNC a little easier

    The string representations of non-alphanum buttons can be found here:

        https://github.com/sibson/vncdotool/blob/master/vncdotool/client.py#L21

    """
    # string of characters where we need to use the shift key;
    # add more chars here if needed, based on string.punctuation minus the non-shifted chars
    _shift_chars = '!"#$%&()*+:<>?@^_{|}~'

    def __init__(self, vnc_client):
        self.client = vnc_client

    # vnc client is a pain to use, so tack on whatever methods you need
    def press(self, key, sleep=.1):
        """Press a single key"""
        if key in self._shift_chars:
            self.client.keyDown('shift')

        # all vncdotool keymapping are lowercase, and all uppercase letters are treated
        # as lowercase anyway (hence the need for this fun shift handling)
        print 'press {}'.format(key)
        self.client.keyPress(key.lower())

        if key in self._shift_chars:
            self.client.keyUp('shift')
        time.sleep(sleep)

    def type(self, keys, sleep=1):
        """Press a sequence of keys

        Since strings are sequences, this can be passed a string, or a list of buttons to press

        """
        for key in keys:
            self.press(key)
        time.sleep(sleep)


class OSConsoleTyper(object):
    """Used to send keypresses to an OpenStack noVNC console

    A selenium WebDriver instance is required as the first argument to the initializer.

    The javascript names for non-alphanumeric keys can be found here:

        https://github.com/kanaka/noVNC/blob/master/include/keysym.js

    For brevity, this class takes the liberty of adding the 'XK_' prefix if it is not already
    appended. The key symbols are case-sensitive, and this class does nothing to help you with that

    While at first glance it might look to be a drop-in replacement for VNCTyper, the key symbol
    names vary wildly between the two implementations.

    Most low-ascii special keys are supported, any other keys can be ground in keysym.js.
    For example, to hit enter, the key symbol is 'XK_Return', or simply 'Return' since this
    class will add the prefix, if needed.

    """
    # map special/shifted chars to their keymap name
    # If javascript explodes with something about a XK_<foo> being undefined,
    # it probably means something needs to get added/fixed here.
    _special_chars = {
        ' ': 'space',
        '!': 'exclam',
        '"': 'quotedbl',
        '#': 'numbersign',
        '%': 'percent',
        '&': 'ampersand',
        "'": 'apostrophe',
        '(': 'parenleft',
        ')': 'parenright',
        '*': 'asterisk',
        '+': 'plus',
        ',': 'comma',
        '-': 'minus',
        '.': 'period',
        '/': 'slash',
        ':': 'colon',
        ';': 'semicolon',
        '<': 'less',
        '=': 'equal',
        '>': 'greater',
        '?': 'question',
        '@': 'at',
        '[': 'bracketleft',
        ']': 'bracketright',
        '^': 'asciicircum',
        '_': 'underscore',
        '`': 'grave',
        '{': 'braceleft',
        '|': 'bar',
        '}': 'braceright',
        '~': 'asciitilde',
        '\\': 'backslash',
    }

    def __init__(self, browser):
        self._browser = browser

    def press(self, key, sleep=.1):
        """Press a single key"""
        if key in self._special_chars:
            key = self._special_chars[key]
        if not key.startswith('XK_'):
            key = 'XK_{}'.format(key)
        self._browser.execute_script('rfb.sendKey({});'.format(key))

        time.sleep(sleep)

    def type(self, keys, sleep=1):
        """Press a sequence of keys

        Since strings are sequences, this can be passed a string, or a list of buttons to press

        """
        for key in keys:
            self.press(key)
        time.sleep(sleep)


def vnc_client(vnc_connect, password='rhci'):
    # Note that the VNC client is pretty rough. It's using a hacked-up twisted implementation
    # that doesn't allow for making more than one connection in a single python process due
    # to an unrestartable twisted reactor. So, one vnc client connection per interpreter :(
    # TODO: Implement a better twisted implementation for the vnc client :)
    print 'Connecting to VNC at {}'.format(vnc_connect)
    client = vnc.connect(vnc_connect, password)
    return VNCTyper(client)


def openstack_vnc_console(vm_name):
    mgmt = get_mgmt()
    instance = find_resource(mgmt.api.servers, vm_name)
    console_url = instance.get_vnc_console('novnc')['console']['url']
    b = browser.ensure_browser_open(console_url)
    return OSConsoleTyper(b)
