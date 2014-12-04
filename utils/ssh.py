import re
import sys
from urlparse import urlparse

import paramiko
from scp import SCPClient

from utils import conf
from utils.log import logger
from utils.net import net_check
from fixtures.pytest_store import store
from utils.timeutil import parsetime


class SSHClient(paramiko.SSHClient):
    """paramiko.SSHClient wrapper

    Allows copying/overriding and use as a context manager
    Constructor kwargs are handed directly to paramiko.SSHClient.connect()
    """
    def __init__(self, stream_output=False, **connect_kwargs):
        super(SSHClient, self).__init__()
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._streaming = stream_output

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

    def __repr__(self):
        return "<SSHClient hostname={}>".format(repr(self._connect_kwargs.get("hostname")))

    def __call__(self, **connect_kwargs):
        # Update a copy of this instance's connect kwargs with passed in kwargs,
        # then return a new instance with the updated kwargs
        new_connect_kwargs = dict(self._connect_kwargs)
        new_connect_kwargs.update(connect_kwargs)
        new_client = SSHClient(**new_connect_kwargs)
        return new_client

    def __enter__(self):
        self.connect(**self._connect_kwargs)
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def connect(self, hostname, *args, **kwargs):
        """See paramiko.SSHClient.connect"""
        port = int(kwargs.get('port', 22))
        if not net_check(port, hostname):
            raise Exception("Connection to %s is not available as port %d is unavailable"
                            % (hostname, port))
        super(SSHClient, self).connect(hostname, *args, **kwargs)

    def run_command(self, command):
        logger.info("Running command `{}`".format(command))
        return command_runner(self, command, self._streaming)

    def run_rails_command(self, command):
        logger.info("Running rails command `{}`".format(command))
        return rails_runner(self, command, self._streaming)

    def run_rake_command(self, command):
        logger.info("Running rake command `{}`".format(command))
        return rake_runner(self, command, self._streaming)

    def put_file(self, local_file, remote_file='.', **kwargs):
        logger.info("Transferring local file {} to remote {}".format(local_file, remote_file))
        return scp_putter(self, local_file, remote_file, **kwargs)

    def get_file(self, remote_file, local_path='', **kwargs):
        logger.info("Transferring remote file {} to local {}".format(remote_file, local_path))
        return scp_getter(self, remote_file, local_path, **kwargs)

    def get_version(self):
        return version_getter(self)

    def get_build_datetime(self):
        return build_datetime_getter(self)

    def is_appliance_downstream(self):
        return is_downstream_getter(self)

    def uptime(self):
        out = self.run_command('cat /proc/uptime')[1]
        match = re.findall('\d+\.\d+', out)

        if match:
            return float(match[0])

        return 0

    def appliance_has_netapp(self):
        return appliance_has_netapp(self)


def command_runner(client, command, stream_output=False):
    template = '%s\n'
    command = template % command
    with client as ctx:
        transport = ctx.get_transport()
        session = transport.open_session()
        session.exec_command(command)
        stdout = session.makefile()
        stderr = session.makefile_stderr()
        output = ''
        while True:
            if session.recv_ready:
                for line in stdout:
                    output += line
                    if stream_output:
                        sys.stdout.write(line)

            if session.recv_stderr_ready:
                for line in stderr:
                    output += line
                    if stream_output:
                        sys.stderr.write(line)

            if session.exit_status_ready():
                break
        exit_status = session.recv_exit_status()
        return exit_status, output

    # Returning two things so tuple unpacking the return works even if the ssh client fails
    return None, None


def rails_runner(client, command, stream_output=False):
    template = 'cd /var/www/miq/vmdb; bin/rails runner %s'
    return command_runner(client, template % command, stream_output)


def rake_runner(client, command, stream_output=False):
    template = 'cd /var/www/miq/vmdb; bin/rake %s'
    return command_runner(client, template % command, stream_output)


def version_getter(client):
    command = 'cd /var/www/miq/vmdb; cat /var/www/miq/vmdb/VERSION'
    x, version = command_runner(client, command, stream_output=False)
    return version.strip()


def build_datetime_getter(client):
    command = "stat --printf=%Y /var/www/miq/vmdb/VERSION"
    x, build_seconds = command_runner(client, command, stream_output=False)
    return parsetime.fromtimestamp(int(build_seconds.strip()))


def is_downstream_getter(client):
    command = "stat /var/www/miq/vmdb/BUILD"
    result = command_runner(client, command, stream_output=False)[0]
    return result == 0


def appliance_has_netapp(client):
    command = "stat /var/www/miq/vmdb/HAS_NETAPP"
    result = command_runner(client, command, stream_output=False)[0]
    return result == 0


def scp_putter(client, local_file, remote_file, **kwargs):
    with client as ctx:
        transport = ctx.get_transport()
        SCPClient(transport).put(local_file, remote_file, **kwargs)


def scp_getter(client, remote_file, local_path, **kwargs):
    with client as ctx:
        transport = ctx.get_transport()
        SCPClient(transport).get(remote_file, local_path, **kwargs)


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
