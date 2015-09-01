import time

from vncdotool import api as vnc

from utils import conf
from utils.ssh import SSHClient


def save_rhci_conf(**rhci_conf_updates):
    """Write the current state of the rhci conf out to the conf yaml"""
    conf.rhci.update(rhci_conf_updates)
    conf.save('rhci')
    return conf.rhci


def ssh_client():
    deployment_conf = conf.rhci['deployments']['basic']['fusor-installer']
    creds = conf.credentials_rhci[deployment_conf['rootpw_credential']]
    return SSHClient(hostname=conf.rhci.ip_address, stream_output=True, **creds)


def inject_credentials():
    # inject the RHCI credentials into the "normal" cloudforms credentials
    # This allows CFME automation to use the RHCI credentials that were used in RHCI setup
    conf.runtime['credentials'].update(conf.credentials_rhci)


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

        self.client.keyPress(key)

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


def vnc_client(vnc_connect, password='rhci'):
    # Note that the VNC client is pretty rough. It's using a hacked-up twisted implementation
    # that doesn't allow for making more than one connection in a single python process due
    # to an unrestartable twisted reactor. So, one vnc client connection per interpreter :(
    # TODO: Implement a better twisted implementation for the vnc client :)
    print 'Connecting to VNC at {}'.format(vnc_connect)
    client = vnc.connect(vnc_connect, password)
    return VNCTyper(client)
