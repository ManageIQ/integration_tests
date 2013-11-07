import paramiko
from scp import SCPClient


class SSHClient(paramiko.SSHClient):
    """paramiko.SSHClient wrapper

    Allows copying/overriding and use as a context manager
    Constructor kwargs are handed directly to paramiko.SSHClient.connect()
    """
    def __init__(self, **connect_kwargs):
        super(SSHClient, self).__init__()
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Set up some sane defaults
        if 'timeout' not in connect_kwargs:
            connect_kwargs['timeout'] = 10
        if 'allow_agent' not in connect_kwargs:
            connect_kwargs['allow_agent'] = False
        if 'look_for_keys' not in connect_kwargs:
            connect_kwargs['look_for_keys'] = False
        self._connect_kwargs = connect_kwargs

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
        return command_runner(self, command)

    def run_rails_command(self, command):
        return rails_runner(self, command)

    def run_rake_command(self, command):
        return rake_runner(self, command)

    def put_file(self, local_file, remote_file='.'):
        return scp_putter(self, local_file, remote_file)

    def get_file(self, remote_file, local_path=''):
        return scp_getter(self, remote_file, local_path)


def command_runner(client, command):
    template = '%s\n'
    command = template % command
    with client as ctx:
        transport = ctx.get_transport()
        session = transport.open_session()
        session.set_combine_stderr(True)
        session.exec_command(command)
        exit_status = session.recv_exit_status()
        output = session.recv(-1)
        return exit_status, output

    # Returning two things so tuple unpacking the return works even if the ssh client fails
    return None, None


def rails_runner(client, command):
    template = '/var/www/miq/vmdb/script/rails runner %s'
    return command_runner(client, template % command)


def rake_runner(client, command):
    template = '/var/www/miq/vmdb/script/rake -f /var/www/miq/vmdb/Rakefile %s'
    return rails_runner(client, template % command)


def scp_putter(client, local_file, remote_file):
    with client as ctx:
        transport = ctx.get_transport()
        SCPClient(transport).put(local_file, remote_file)


def scp_getter(client, remote_file, local_path):
    with client as ctx:
        transport = ctx.get_transport()
        SCPClient(transport).get(remote_file, local_path)
