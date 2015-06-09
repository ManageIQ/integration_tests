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
from utils.wait import wait_for


# Default blocking time before giving up on an ssh command execution,
# in seconds (float)
RUNCMD_TIMEOUT = 1200.0
SSHResult = namedtuple("SSHResult", ["rc", "output"])

_ssh_key_file = project_path.join('.generated_ssh_key')
_ssh_pubkey_file = project_path.join('.generated_ssh_key.pub')

# enum
_ssh_keystate = AttrDict({
    'not_installed': 0,
    'installing': 1,
    'installed': 2
})
# enum reverse lookup
_ssh_keystate.update({v: k for k, v in _ssh_keystate.items()})


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
        logger.debug('client initialized with keystate {}'.format(_ssh_keystate[keystate]))

        # Load credentials and destination from confs, set up sane defaults
        parsed_url = urlparse(store.base_url)
        default_connect_kwargs = {
            'username': conf.credentials['ssh']['username'],
            'password': conf.credentials['ssh']['password'],
            'hostname': parsed_url.hostname,
            'timeout': 10,
            'allow_agent': False,
            'look_for_keys': False,
            'gss_auth': False
        }

        # Overlay defaults with any passed-in kwargs and store
        default_connect_kwargs.update(connect_kwargs)
        self._connect_kwargs = default_connect_kwargs
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())

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
        self.connect()
        return self

    def __exit__(self, *args, **kwargs):
        # Noop, call close explicitly to shut down the transport
        # It will be reopened automatically on next command
        pass

    def _check_port(self):
        hostname = self._connect_kwargs['hostname']
        port = int(self._connect_kwargs.get('port', 22))
        if not net_check(port, hostname):
            raise Exception("SSH connection to %s:%d failed, port unavailable".format(
                hostname, port))

    def _progress_callback(self, filename, size, sent):
        sent_percent = (sent * 100.) / size
        if sent_percent > 0:
            logger.debug('{} scp progress: {:.2f}% '.format(filename, sent_percent))

    @property
    def connected(self):
        return self._transport and self._transport.active

    def connect(self, hostname=None, **kwargs):
        """See paramiko.SSHClient.connect"""
        if hostname and hostname != self._connect_kwargs['hostname']:
            self._connect_kwargs['hostname'] = hostname
            self.close()

        if not self.connected:
            self._connect_kwargs.update(kwargs)
            self._check_port()
            # Only install ssh keys if they aren't installed (or currently being installed)
            if self._keystate < _ssh_keystate.installing:
                self.install_ssh_keys()
            return super(SSHClient, self).connect(**self._connect_kwargs)

    def get_transport(self, *args, **kwargs):
        if self.connected:
            logger.trace('reusing ssh transport')
        else:
            logger.trace('connecting new ssh transport')
            self.connect()
        return super(SSHClient, self).get_transport(*args, **kwargs)

    def run_command(self, command, timeout=RUNCMD_TIMEOUT, padding=0, log=True):
        if log:
            logger.info("{}Running command `{}`".format(padding * " ", command))
        template = '%s\n'
        command = template % command

        try:
            session = self.get_transport().open_session()
            if timeout:
                session.settimeout(float(timeout))
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

    def run_rails_command(self, command, timeout=RUNCMD_TIMEOUT):
        logger.info("Running rails command `{}`".format(command))
        return self.run_command('cd /var/www/miq/vmdb; bin/rails runner {}'.format(command),
            timeout=timeout)

    def run_rake_command(self, command, timeout=RUNCMD_TIMEOUT):
        logger.info("Running rake command `{}`".format(command))
        return self.run_command('cd /var/www/miq/vmdb; bin/rake {}'.format(command),
            timeout=timeout)

    def put_file(self, local_file, remote_file='.', **kwargs):
        logger.info("Transferring local file {} to remote {}".format(local_file, remote_file))
        return SCPClient(self.get_transport(), progress=self._progress_callback).put(
            local_file, remote_file, **kwargs)

    def get_file(self, remote_file, local_path='', **kwargs):
        logger.info("Transferring remote file {} to local {}".format(remote_file, local_path))
        return SCPClient(self.get_transport(), progress=self._progress_callback).get(
            remote_file, local_path, **kwargs)

    def get_version(self):
        return self.run_command(
            'cd /var/www/miq/vmdb; cat /var/www/miq/vmdb/VERSION').output.strip()

    def get_build_datetime(self):
        command = "stat --printf=%Y /var/www/miq/vmdb/VERSION"
        return parsetime.fromtimestamp(int(self.run_command(command).output.strip()))

    def get_build_date(self):
        return self.get_build_datetime().date()

    def is_appliance_downstream(self):
        return self.run_command("stat /var/www/miq/vmdb/BUILD").rc == 0

    def uptime(self):
        out = self.run_command('cat /proc/uptime')[1]
        match = re.findall('\d+\.\d+', out)

        if match:
            return float(match[0])

        return 0

    def client_address(self):
        res = self.run_command('echo $SSH_CLIENT')
        # SSH_CLIENT format is 'clientip clientport serverport', we want clientip
        return res.output.split()[0]

    def appliance_has_netapp(self):
        return self.run_command("stat /var/www/miq/vmdb/HAS_NETAPP").rc == 0

    def install_ssh_keys(self, padding=0):
        self.wait_ssh()
        self._keystate = _ssh_keystate.installing
        if not _ssh_key_file.check():
            keygen()
        self._connect_kwargs['key_filename'] = _ssh_key_file.strpath

        if self.run_command('test -f ~/.ssh/authorized_keys', padding=padding + 1).rc != 0:
            self.run_command('mkdir -p ~/.ssh', padding=padding + 1)
            self.put_file(_ssh_key_file.strpath, '~/.ssh/id_rsa')
            self.put_file(_ssh_pubkey_file.strpath, '~/.ssh/id_rsa.pub')
            self.run_command('cp ~/.ssh/id_rsa.pub ~/.ssh/authorized_keys;'
                'chmod 700 ~/.ssh; chmod 600 ~/.ssh/*', padding=padding + 1)
        self._keystate = _ssh_keystate.installed

    def wait_ssh(self):
        def _wait_f():
            try:
                return self.run_command("true", log=False).rc == 0
            except (EOFError, paramiko.SSHException) as e:
                logger.info(" SSH not available yet ({}: {})".format(type(e).__name__, str(e)))
                return False

        wait_for(_wait_f, num_sec=60, delay=5, message="SSH available")


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
