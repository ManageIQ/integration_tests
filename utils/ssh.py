import sys
from urlparse import urlparse

import paramiko
from scp import SCPClient

from utils import conf
from utils.net import net_check


class SSHClient(paramiko.SSHClient):
    """paramiko.SSHClient wrapper

    Allows copying/overriding and use as a context manager
    Constructor kwargs are handed directly to paramiko.SSHClient.connect()
    """
    def __init__(self, stream_output=False, **connect_kwargs):
        port = connect_kwargs.get('port', 22)
        addr = connect_kwargs.get('hostname', None)
        if not net_check(port, addr=addr):
            raise Exception("Connection is not available as port is unavailable")
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
        parsed_url = urlparse(conf.env['base_url'])
        default_connect_kwargs = {
            'username': conf.credentials['ssh']['username'],
            'password': conf.credentials['ssh']['password'],
            'hostname': parsed_url.hostname,
        }

        # Overlay defaults with any passed-in kwargs and store
        default_connect_kwargs.update(connect_kwargs)
        self._connect_kwargs = default_connect_kwargs

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

    def run_command(self, command):
        return command_runner(self, command, self._streaming)

    def run_rails_command(self, command):
        return rails_runner(self, command, self._streaming)

    def run_rake_command(self, command):
        return rake_runner(self, command, self._streaming)

    def put_file(self, local_file, remote_file='.', **kwargs):
        return scp_putter(self, local_file, remote_file, **kwargs)

    def get_file(self, remote_file, local_path='', **kwargs):
        return scp_getter(self, remote_file, local_path, **kwargs)

    def get_version(self):
        return version_getter(self)


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
    if version.strip().lower() == "master":
        return "9.9.9.9"  # They have changed it
    return version.strip()


def scp_putter(client, local_file, remote_file, **kwargs):
    with client as ctx:
        transport = ctx.get_transport()
        SCPClient(transport).put(local_file, remote_file, **kwargs)


def scp_getter(client, remote_file, local_path, **kwargs):
    with client as ctx:
        transport = ctx.get_transport()
        SCPClient(transport).get(remote_file, local_path, **kwargs)
