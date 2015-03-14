# coding: utf-8 -*-
import re
import sys
from collections import namedtuple
from urlparse import urlparse

import paramiko
from lya import AttrDict
from scp import SCPClient

from utils import conf
from utils.log import logger
from utils.net import net_check
from fixtures.pytest_store import store
from utils.path import project_path
from utils.timeutil import parsetime


SSHResult = namedtuple("SSHResult", ["rc", "output"])

_ssh_key_file = project_path.join('.generated_ssh_key')
_ssh_pubkey_file = project_path.join('.generated_ssh_key.pub')

# enum
_ssh_keystate = AttrDict({
    'not_installed': 0,
    'installing': 1,
    'installed': 2
})


class SSHClient(paramiko.SSHClient):
    """paramiko.SSHClient wrapper

    Allows copying/overriding and use as a context manager
    Constructor kwargs are handed directly to paramiko.SSHClient.connect()
    """
    def __init__(self, stream_output=False, keystate=_ssh_keystate.not_installed,
            **connect_kwargs):
        super(SSHClient, self).__init__()
        self._streaming = stream_output
        self._keystate = keystate

        # Set up some sane defaults
        default_connect_kwargs = dict()
        if 'timeout' not in connect_kwargs:
            default_connect_kwargs['timeout'] = 10
        if 'allow_agent' not in connect_kwargs:
            default_connect_kwargs['allow_agent'] = False
        if 'look_for_keys' not in connect_kwargs:
            default_connect_kwargs['look_for_keys'] = False

        # Load credentials and destination from confs
        parsed_url = urlparse(store.base_url)
        default_connect_kwargs = {
            'username': conf.credentials['ssh']['username'],
            'password': conf.credentials['ssh']['password'],
            'hostname': parsed_url.hostname,
        }

        # Overlay defaults with any passed-in kwargs and store
        default_connect_kwargs.update(connect_kwargs)
        self._connect_kwargs = default_connect_kwargs
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    @property
    def transport(self):
        with self:
            return self._transport

    def __repr__(self):
        return "<SSHClient hostname={}>".format(repr(self._connect_kwargs.get("hostname")))

    def __call__(self, **connect_kwargs):
        # Update a copy of this instance's connect kwargs with passed in kwargs,
        # then return a new instance with the updated kwargs
        new_connect_kwargs = dict(self._connect_kwargs)
        new_connect_kwargs.update(connect_kwargs)
        # pass the key state if the hostname is the same, under the assumption that the same
        # host will still have keys installed if they have already been
        if self._connect_kwargs['hostname'] == new_connect_kwargs.get('hostname'):
            new_connect_kwargs['keystate'] = self._keystate
        new_client = SSHClient(**new_connect_kwargs)
        return new_client

    def __enter__(self):
        if self._transport is None:
            self.connect(**self._connect_kwargs)
        return self

    def __exit__(self, *args, **kwargs):
        # Noop, call clone explicitly to shut down the transport
        pass

    def connect(self, hostname, *args, **kwargs):
        """See paramiko.SSHClient.connect"""
        port = int(kwargs.get('port', 22))
        if not net_check(port, hostname):
            raise Exception("Connection to %s is not available as port %d is unavailable"
                            % (hostname, port))
        # Only install ssh keys if they aren't installed (or currently being installed)
        if self._keystate < _ssh_keystate.installing:
            self.install_ssh_keys()
        super(SSHClient, self).connect(hostname, *args, **kwargs)

    def run_command(self, command):
        logger.info("Running command `{}`".format(command))
        template = '%s\n'
        command = template % command

        try:
            session = self.transport.open_session()
            session.exec_command(command)
            stdout = session.makefile()
            stderr = session.makefile_stderr()
            output = ''
            while True:
                if session.recv_ready:
                    for line in stdout:
                        output += line
                        if self._streaming:
                            sys.stdout.write(line)

                if session.recv_stderr_ready:
                    for line in stderr:
                        output += line
                        if self._streaming:
                            sys.stderr.write(line)

                if session.exit_status_ready():
                    break
            exit_status = session.recv_exit_status()
            return SSHResult(exit_status, output)
        except paramiko.SSHException as exc:
            logger.exception(exc)

        # Returning two things so tuple unpacking the return works even if the ssh client fails
        return SSHResult(1, None)

    def run_rails_command(self, command):
        logger.info("Running rails command `{}`".format(command))
        return self.run_command('cd /var/www/miq/vmdb; bin/rails runner {}'.format(command))

    def run_rake_command(self, command):
        logger.info("Running rake command `{}`".format(command))
        return self.run_command('cd /var/www/miq/vmdb; bin/rake {}'.format(command))

    def put_file(self, local_file, remote_file='.', **kwargs):
        logger.info("Transferring local file {} to remote {}".format(local_file, remote_file))
        return SCPClient(self.transport).put(local_file, remote_file, **kwargs)

    def get_file(self, remote_file, local_path='', **kwargs):
        logger.info("Transferring remote file {} to local {}".format(remote_file, local_path))
        return SCPClient(self.transport).get(remote_file, local_path, **kwargs)

    def get_version(self):
        return self.run_command(
            'cd /var/www/miq/vmdb; cat /var/www/miq/vmdb/VERSION').output.strip()

    def get_build_datetime(self):
        command = "stat --printf=%Y /var/www/miq/vmdb/VERSION"
        return parsetime.fromtimestamp(int(self.run_command(command).output.strip()))

    def is_appliance_downstream(self):
        return self.run_command("stat /var/www/miq/vmdb/BUILD").rc == 0

    def uptime(self):
        out = self.run_command('cat /proc/uptime')[1]
        match = re.findall('\d+\.\d+', out)

        if match:
            return float(match[0])

        return 0

    def appliance_has_netapp(self):
        return self.run_command("stat /var/www/miq/vmdb/HAS_NETAPP").rc == 0

    def install_ssh_keys(self):
        self._keystate = _ssh_keystate.installing
        if not _ssh_key_file.check():
            keygen()

        if self.run_command('test -f ~/.ssh/authorized_keys').rc != 0:
            self.run_command('mkdir -p ~/.ssh')
            self.put_file(_ssh_key_file.strpath, '~/.ssh/id_rsa')
            self.put_file(_ssh_pubkey_file.strpath, '~/.ssh/id_rsa.pub')
            self.run_command('cp ~/.ssh/id_rsa.pub ~/.ssh/authorized_keys;'
                'chmod 700 ~/.ssh; chmod 600 ~/.ssh/*')
        self._keystate = _ssh_keystate.installed


class SSHTail(SSHClient):

    def __init__(self, remote_filename, **connect_kwargs):
        super(SSHTail, self).__init__(stream_output=False, **connect_kwargs)
        self._remote_filename = remote_filename
        self._sftp_client = None
        self._remote_file_size = None

    def __iter__(self):
        with self as sshtail:
            fstat = sshtail._sftp_client.stat(self._remote_filename)
            if self._remote_file_size is not None:
                if self._remote_file_size < fstat.st_size:
                    remote_file = self._sftp_client.open(self._remote_filename, 'r')
                    remote_file.seek(self._remote_file_size, 0)
                    while (remote_file.tell() < fstat.st_size):
                        line = remote_file.readline().rstrip()
                        yield line
            self._remote_file_size = fstat.st_size

    def __enter__(self):
        self.connect(**self._connect_kwargs)
        self._sftp_client = self.open_sftp()
        return self

    def __exit__(self, *args, **kwargs):
        self._sftp_client.close()

    def set_initial_file_end(self):
        with self as sshtail:
            fstat = sshtail._sftp_client.stat(self._remote_filename)
            self._remote_file_size = fstat.st_size  # Seed initial size of file


def keygen():
    """Generate temporary ssh keypair for appliance SSH auth

    Intended not only to simplify ssh access to appliances, but also to simplify
    SSH access from one appliance to another in multi-appliance setups

    """
    # private key
    prv = paramiko.RSAKey.generate(bits=1024)
    with _ssh_key_file.open('w') as f:
        prv.write_private_key(f)

    # public key
    pub = paramiko.RSAKey(filename=_ssh_key_file.strpath)
    with _ssh_pubkey_file.open('w') as f:
        f.write("{} {} {}".format(pub.get_name(), pub.get_base64(),
            'autogenerated cfme_tests key'))
