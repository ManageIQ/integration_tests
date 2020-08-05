import re
import socket
import sys
import typing
from functools import total_ordering
from os import path as os_path
from subprocess import check_call

import attr
import fauxfactory
import gevent
import iso8601
import paramiko
from cached_property import cached_property
from scp import SCPClient
from wrapanapi.entities import Vm

from cfme.fixtures.pytest_store import store
from cfme.utils import conf
from cfme.utils import ports
from cfme.utils.log import logger
from cfme.utils.net import net_check
from cfme.utils.net import retry_connect
from cfme.utils.path import project_path
from cfme.utils.quote import quote
from cfme.utils.timeutil import parsetime
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker
from cfme.utils.wait import wait_for

# We need the Credential only for type checking and there is a circular import if imported
# unconditionally. This is a hacky way to work this around.
if typing.TYPE_CHECKING:
    from cfme.base.credential import Credential

# Default blocking time before giving up on an ssh command execution,
# in seconds (float)
RUNCMD_TIMEOUT = 1200.0
CONNECT_RETRIES_TIMEOUT = 2 * 60
CONNECT_TIMEOUT = 10
CONNECT_SSH_DELAY = 1


@attr.s(frozen=True, eq=False)
@total_ordering
class SSHResult:
    """Allows rich comparison for more convenient testing.

    Given you have ``result`` which is an instance of :py:class:`SSHResult`, you can do as follows

    .. code-block:: python

        assert result  # If $?=0, then the result evaluates to a truthy value and passes the assert
        assert result == 'installed'  # direct matching of the output value
        assert 'something' in result  # like before but uses the ``in`` matching for a partial match
        assert result == 5  # assert that the $?=5 (you can use <, >, ...)

    Therefore this class can act like 3 kinds of values

    - Like a string (with the output of the command) when compared with or cast to one
    - Like a number (with the return code) when compared with or cast to one
    - Like a bool, giving truthy value if the return code was zero. That is related to the
      preceeding bullet.

    But it still subclasses the original class therefore all old behaviour is kept. But you don't
    have to expand the tuple or pull the value out if you are checking only one of them.
    """
    command = attr.ib()
    rc = attr.ib()
    output = attr.ib(repr=False)

    def __str__(self):
        return str(self.output)

    def __contains__(self, what):
        # Handling 'something' in x
        if not isinstance(what, str):
            raise ValueError('You can only check strings using the in operator')
        return what in self.output

    def __bool__(self):
        # Handling bool(x) or if x:
        return self.rc == 0

    def __int__(self):
        # handling int(x)
        return self.rc

    def __eq__(self, other):
        if isinstance(other, int):
            return self.rc == other
        elif isinstance(other, str):
            return self.output == other
        else:
            raise ValueError('You can only compare SSHResult with str or int')

    def __lt__(self, other):
        if isinstance(other, int):
            return self.rc < other
        elif isinstance(other, str):
            return self.output < other
        else:
            raise ValueError('You can only compare SSHResult with str or int')

    @property
    def success(self):
        return self.rc == 0

    @property
    def failed(self):
        return self.rc != 0


_ssh_key_file = project_path.join('.generated_ssh_key')
_ssh_pubkey_file = project_path.join('.generated_ssh_key.pub')

_client_session = list()


class SSHClient(paramiko.SSHClient):
    """paramiko.SSHClient wrapper

    Allows copying/overriding and use as a context manager
    Constructor kwargs are handed directly to paramiko.SSHClient.connect()

    Args:
        container: If specified, then it is assumed that the VM hosts a container of CFME. The
            param then contains the name of the container.
        project: openshift's project which holds CFME pods
        is_pod: If specified and True, then it is assumed that the target is a podified openshift
            app and ``container`` then specifies the name of the pod to interact with.
        stdout: If specified, overrides the system stdout file for streaming output.
        stderr: If specified, overrides the system stderr file for streaming output.
    """
    def __init__(self, *, stream_output=False, **connect_kwargs):
        super().__init__()
        self._streaming = stream_output
        # deprecated/useless karg, included for backward-compat
        self._keystate = connect_kwargs.pop('keystate', None)
        # Container is used to store both docker VM's container name and Openshift pod name.
        self._container = connect_kwargs.pop('container', None)
        self._project = connect_kwargs.pop('project', None)
        self.is_pod = connect_kwargs.pop('is_pod', False)
        self.is_dev = connect_kwargs.pop('is_dev', False)
        self.oc_username = connect_kwargs.pop('oc_username', None)
        self.oc_password = connect_kwargs.pop('oc_password', False)
        self.f_stdout = connect_kwargs.pop('stdout', sys.stdout)
        self.f_stderr = connect_kwargs.pop('stderr', sys.stderr)
        self._use_check_port = connect_kwargs.pop('use_check_port', True)
        self.strict_host_key_checking = connect_kwargs.pop('strict_host_key_checking', True)

        # load the defaults for ssh, including current_appliance and default credentials keys
        compiled_kwargs = dict(
            timeout=CONNECT_TIMEOUT,
            allow_agent=False,
            look_for_keys=False,
            gss_auth=False,
            username=conf.credentials['ssh']['username'],
            password=conf.credentials['ssh']['password'],
            port=ports.SSH,
        )

        # Overlay defaults with any passed-in kwargs and assign to _connect_kwargs
        compiled_kwargs.update(connect_kwargs)
        if not compiled_kwargs.get("hostname"):
            compiled_kwargs["hostname"] = store.current_appliance.hostname

        self._connect_kwargs = compiled_kwargs
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        _client_session.append(self)

    def tunnel_to(self, **kwargs):
        """
        Tunnels the SSH session trough the host this client is connected to to other host.
        All parameters are the same as for the `SSHClient.__init__`
        """
        transport: 'paramiko.Transport' = self.get_transport()

        # It seems this is not really in any use in our case, but something has to be specified as
        # the local address and port.
        # https://github.com/paramiko/paramiko/issues/1410
        # https://github.com/paramiko/paramiko/issues/1485
        local_addr = ('0.0.0.0', 0)

        dest_addr = (kwargs['hostname'], kwargs.get('port', ports.SSH))
        channel = transport.open_channel("direct-tcpip", dest_addr, local_addr)

        dest_client = SSHClient(**kwargs, sock=channel, use_check_port=False)
        return dest_client

    @property
    def is_container(self):
        return self._container is not None and not self.is_pod

    @cached_property
    def vmdb_version(self):
        res = self.run_command('cat /var/www/miq/vmdb/VERSION')
        if res.failed:
            raise RuntimeError(f'Unable to retrieve appliance VMDB version: {res.output}')
        version_string = res.output
        return Version(version_string)

    @property
    def username(self):
        return self._connect_kwargs.get('username')

    def __repr__(self):
        return "<SSHClient hostname={} port={}>".format(
            repr(self._connect_kwargs.get("hostname")),
            repr(self._connect_kwargs.get("port", 22)))

    def __call__(self, **connect_kwargs):
        # Update a copy of this instance's connect kwargs with passed in kwargs,
        # then return a new instance with the updated kwargs
        new_connect_kwargs = dict(self._connect_kwargs)
        new_connect_kwargs.update(connect_kwargs)
        # pass the key state if the hostname is the same, under the assumption that the same
        # host will still have keys installed if they have already been
        new_client = SSHClient(**new_connect_kwargs)
        return new_client

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args, **kwargs):
        # Noop, call close explicitly to shut down the transport
        # It will be reopened automatically on next command
        pass

    def __del__(self):
        self.close()

    def _check_port(self):
        hostname = self._connect_kwargs['hostname']
        if not net_check(ports.SSH, hostname, force=True):
            raise Exception("SSH connection to {}:{} failed, port unavailable".format(
                hostname, ports.SSH))

    def _progress_callback(self, filename, size, sent):
        if sent > 0:
            logger.debug('scp progress for %r: %s of %s ', filename, sent, size)

    def close(self):
        super().close()
        try:
            _client_session.remove(self)
        except (AttributeError, ValueError):
            pass

    @property
    def connected(self):
        return self._transport and self._transport.active

    def connect(self, hostname=None, **kwargs):
        if self.is_dev:
            raise Exception('SSH is not allowed using a dev appliance!')
        """See paramiko.SSHClient.connect"""
        if hostname and hostname != self._connect_kwargs['hostname']:
            self._connect_kwargs['hostname'] = hostname
            self.close()

        if not self.connected:
            self._connect_kwargs.update(kwargs)
            if self._use_check_port:
                wait_for(self._check_port, handle_exception=True,
                         timeout=CONNECT_TIMEOUT, delay=5)
            try:
                conn = super().connect(**self._connect_kwargs)
            except paramiko.ssh_exception.BadHostKeyException:
                if self.strict_host_key_checking:
                    raise

                hk = self.get_host_keys()
                del hk[self._connect_kwargs['hostname']]
                conn = super().connect(**self._connect_kwargs)
                logger.warning('Host key for host %s changed. Using the new one as '
                               'strict_host_key_checking is disabled.',
                               self._connect_kwargs['hostname'])
        else:
            conn = None

        self._after_connect()
        return conn

    def _after_connect(self):
        if self.is_pod:
            # checking whether already logged into openshift
            is_loggedin = self.run_command(command='oc whoami', ensure_host=True)
            if is_loggedin.success:
                username = str(is_loggedin).strip()
                logger.info(f'user {username} is already logged in')
                if username != self.oc_username:
                    logger.info('logging out from openshift')
                    self.run_command(command='oc logout', ensure_host=True)
                else:
                    return

            logger.info("logging into openshift")
            login_cmd = 'oc login --username={u} --password={p}'
            login_cmd = login_cmd.format(u=self.oc_username,
                                         p=self.oc_password)
            self.run_command(command=login_cmd, ensure_host=True)

    def open_sftp(self, *args, **kwargs):
        if self.is_container:
            logger.warning(
                'You are about to use sftp on a containerized appliance. It may not work.')
        self.connect()
        return super().open_sftp(*args, **kwargs)

    def get_transport(self, *args, **kwargs):
        if not self.connected:
            self.connect()
        return super().get_transport(*args, **kwargs)

    def run_command(self, command, timeout=RUNCMD_TIMEOUT, ensure_host=False,
                    ensure_user=False, container=None):
        """Run a command over SSH.

        Args:
            command: The command. Supports taking dicts as version picking.
            timeout: Timeout after which the command execution fails.
            ensure_host: Ensure that the command is run on the machine with the IP given, not any
                container or such that we might be using by default.
            ensure_user: Ensure that the command is run as the user we logged in, so in case we are
                not root, setting this to True will prevent from running sudo.
            container: allows to temporarily override default container
        Returns:
            A :py:class:`SSHResult` instance.
        """
        # paramiko hangs on *_ready calls if destination has become unavailable
        # this is some kind of watchdog to handle this issue
        try:
            with gevent.Timeout(timeout):
                return self._run_command(command, timeout, ensure_host, ensure_user,
                                         container)
        except gevent.Timeout:
            logger.error("command %s couldn't finish in given timeout %s", command, timeout)
            raise

    def load_host_keys(self, filename):
        """
        Load host keys from a local host-key file.  Host keys read with this
        method will be checked after keys loaded via `load_system_host_keys`,
        but will be saved back by `save_host_keys` (so they can be modified).
        The missing host key policy `.AutoAddPolicy` adds keys to this set and
        saves them, when connecting to a previously-unknown server.

        This method can be called multiple times.  Each new set of host keys
        will be merged with the existing set (new replacing old if there are
        conflicts).  When automatically saving, the last hostname is used.

        :param str filename: the filename to read

        :raises: ``IOError`` -- if the filename could not be read
        """
        if self.strict_host_key_checking:
            self._host_keys_filename = filename
            self._host_keys.load(filename)

    def load_system_host_keys(self, filename=None):
        """
        Load host keys from a system (read-only) file.  Host keys read with
        this method will not be saved back by `save_host_keys`.

        This method can be called multiple times.  Each new set of host keys
        will be merged with the existing set (new replacing old if there are
        conflicts).

        If ``filename`` is left as ``None``, an attempt will be made to read
        keys from the user's local "known hosts" file, as used by OpenSSH,
        and no exception will be raised if the file can't be read.  This is
        probably only useful on posix.

        :param str filename: the filename to read, or ``None``

        :raises: ``IOError`` --
            if a filename was provided and the file could not be read
        """
        if self.strict_host_key_checking:
            if filename is None:
                # try the user's .ssh key file, and mask exceptions
                filename = os_path.expanduser("~/.ssh/known_hosts")
                try:
                    self._system_host_keys.load(filename)
                except OSError:
                    pass
                return
            self._system_host_keys.load(filename)

    def _run_command(self, command, timeout=RUNCMD_TIMEOUT, ensure_host=False,
                     ensure_user=False, container=None):
        if isinstance(command, dict):
            command = VersionPicker(command).pick(self.vmdb_version)
        original_command = command
        uses_sudo = False
        logger.info("Running command %r", command)
        container = container or self._container
        if self.is_pod and not ensure_host:
            # This command will be executed in the context of the host provider
            command_to_run = '[[ -f /etc/default/evm ]] && source /etc/default/evm; ' + command
            oc_cmd = 'oc exec --namespace={proj} {pod} -- bash -c {cmd}'.format(
                proj=self._project, pod=container, cmd=quote(command_to_run))
            command = oc_cmd
            ensure_host = True
        elif self.is_container and not ensure_host:
            command = 'docker exec {} bash -c {}'.format(container, quote(
                'source /etc/default/evm; ' + command))

        if self.username != 'root' and not ensure_user:
            # We need sudo
            command = 'sudo -i bash -c {command}'.format(command=quote(command))
            uses_sudo = True

        if command != original_command:
            logger.info("> Actually running command %r", command)
        command += '\n'

        output = []
        try:
            session = self.get_transport().open_session()
            if uses_sudo:
                # We need a pseudo-tty for sudo
                session.get_pty()
            if timeout:
                session.settimeout(float(timeout))

            session.exec_command(command)
            stdout = session.makefile()
            stderr = session.makefile_stderr()

            def write_output(line, file):
                output.append(line)
                if self._streaming:
                    file.write(line)

            while True:
                if session.exit_status_ready():
                    break
                no_data = 0
                # While the program is running loop through collecting line by line so that we don't
                # fill the buffers up without a newline.
                # Also, note that for long running programs if we try to read output when there
                # is none (and in the case of stderr may never be any)
                # we risk blocking so long that the write buffer on the remote side will fill
                # and the remote program will block on a write.
                # The blocking on our side occurs in paramiko's buffered_pipe.py's read() call,
                # which will block if its internal buffer is empty.
                if session.recv_ready():
                    try:
                        line = next(stdout)
                        write_output(line, self.f_stdout)
                    except StopIteration:
                        pass
                else:
                    no_data += 1

                if session.recv_stderr_ready():
                    try:
                        line = next(stderr)
                        write_output(line, self.f_stderr)
                    except StopIteration:
                        pass
                else:
                    no_data += 1

                if no_data == 2:
                    gevent.sleep(0.01)

            # When the program finishes, we need to grab the rest of the output that is left.
            # Also, we don't have the issue of blocking reads because since the command is
            # finished, any pending reads of SSH encrypted data will finish shortly and put in
            # the buffer or for an empty file EOF will be reached as it will be closed.
            for line in stdout:
                write_output(line, self.f_stdout)
            for line in stderr:
                write_output(line, self.f_stderr)

            exit_status = session.recv_exit_status()
            if exit_status != 0:
                logger.warning('Exit code %d!', exit_status)
            return SSHResult(rc=exit_status, output=''.join(output), command=command)
        except socket.timeout:
            logger.exception(
                "Command %r timed out. Output before it failed was:\n%r",
                command,
                ''.join(output))
            raise

        # Returning two things so tuple unpacking the return works even if the ssh client fails
        # Return whatever we have in the output
        return SSHResult(rc=1, output=''.join(output), command=command)

    def cpu_spike(self, seconds=60, cpus=2, **kwargs):
        """Creates a CPU spike of specific length and processes.

        Args:
            seconds: How long the spike should last.
            cpus: How many processes to use.

        Returns:
            See :py:meth:`SSHClient.run_command`
        """
        return self.run_command(
            "duration={}; instances={}; endtime=$(($(date +%s) + $duration)); "
            "for ((i=0; i<instances; i++)) do while (($(date +%s) < $endtime)); "
            "do :; done & done".format(seconds, cpus), **kwargs)

    def run_rails_command(self, command, timeout=RUNCMD_TIMEOUT, **kwargs):
        logger.info("Running rails command %r", command)
        return self.run_command('cd /var/www/miq/vmdb; bin/rails runner {command}'.format(
            command=command), timeout=timeout, **kwargs)

    def run_rails_console(self, command, sandbox=False, timeout=RUNCMD_TIMEOUT):
        """Runs Ruby inside of rails console. stderr is thrown away right now but could prove useful
        for future performance analysis of the queries rails runs.  The command is encapsulated by
        double quotes. Sandbox rolls back all changes made to the database if used.
        """
        if sandbox:
            return self.run_command('cd /var/www/miq/vmdb; echo \"{}\" '
                '| bundle exec bin/rails c -s 2> /dev/null'.format(command), timeout=timeout)
        return self.run_command('cd /var/www/miq/vmdb; echo \"{}\" '
            '| bundle exec bin/rails c 2> /dev/null'.format(command), timeout=timeout)

    def run_rake_command(self, command, timeout=RUNCMD_TIMEOUT, rake_cmd_prefix='', **kwargs):
        logger.info("Running rake command %r", command)
        return self.run_command(
            'cd /var/www/miq/vmdb; {pre} bin/rake -f /var/www/miq/vmdb/Rakefile {command}'.format(
                command=command, pre=rake_cmd_prefix), timeout=timeout, **kwargs)

    def put_file(self, local_file, remote_file='.', **kwargs):
        ensure_host = kwargs.pop('ensure_host', False)
        logger.info("Transferring local file %r to remote %r", local_file, remote_file)
        if self.is_container and not ensure_host:
            tempfilename = f'/share/temp_{fauxfactory.gen_alpha()}'
            logger.info('For this purpose, temporary file name is %r', tempfilename)
            scp = SCPClient(self.get_transport(), progress=self._progress_callback).put(
                local_file, tempfilename, **kwargs)
            self.run_command(f'mv {tempfilename} {remote_file}')
            return scp
        elif self.is_pod and not ensure_host:
            tmp_folder_name = fauxfactory.gen_alpha(15, start="automation-").lower()
            logger.info('For this purpose, temporary folder name is /tmp/%s', tmp_folder_name)
            # Clean up container's temporary folder
            self.run_command(f'rm -rf /tmp/{tmp_folder_name}')
            # Create/Clean up the host's temporary folder
            self.run_command(
                'rm -rf /tmp/{0}; mkdir -p /tmp/{0}'.format(tmp_folder_name), ensure_host=True)
            # Now upload the file to the openshift host
            tmp_file_name = fauxfactory.gen_alpha(start="file-").lower()
            tmp_full_name = f'/tmp/{tmp_folder_name}/{tmp_file_name}'
            scp = SCPClient(self.get_transport(), progress=self._progress_callback).put(
                local_file, tmp_full_name, **kwargs)
            # use oc rsync to put the file in the container
            rsync_cmd = 'oc rsync --namespace={proj} /tmp/{file} {pod}:/tmp/'
            assert self.run_command(rsync_cmd.format(proj=self._project, file=tmp_folder_name,
                                                     pod=self._container),
                                    ensure_host=True)
            # Move the file onto correct place
            assert self.run_command(f'mv {tmp_full_name} {remote_file}')
            return scp
        else:
            if self.username == 'root':
                return SCPClient(self.get_transport(), progress=self._progress_callback).put(
                    local_file, remote_file, **kwargs)
            # scp client is not sudo, may not work for non sudo
            tempfilename = '/home/{user_name}/temp_{random_alpha}'.format(
                user_name=self.username, random_alpha=fauxfactory.gen_alpha())
            logger.info('For this purpose, temporary file name is %r', tempfilename)
            scp = SCPClient(self.get_transport(), progress=self._progress_callback).put(
                local_file, tempfilename, **kwargs)
            self.run_command('mv {temp_file} {remote_file}'.format(temp_file=tempfilename,
                                                                   remote_file=remote_file))
            return scp

    def get_file(self, remote_file, local_path='', **kwargs):
        logger.info("Transferring remote file %r to local %r", remote_file, local_path)
        base_name = os_path.basename(remote_file)
        if self.is_container:
            tmp_file_name = fauxfactory.gen_alpha(start="temp_")
            tempfilename = f'/share/{tmp_file_name}'
            logger.info('For this purpose, temporary file name is %r', tempfilename)
            self.run_command(f'cp {remote_file} {tempfilename}')
            scp = SCPClient(self.get_transport(), progress=self._progress_callback).get(
                tempfilename, local_path, **kwargs)
            self.run_command(f'rm {tempfilename}')
            check_call([
                'mv',
                os_path.join(local_path, tmp_file_name),
                os_path.join(local_path, base_name)])
            return scp
        elif self.is_pod:
            tmp_folder_name = fauxfactory.gen_alpha(start="automation-").lower()
            tmp_file_name = fauxfactory.gen_alpha(start="file-").lower()
            tmp_full_name = f'/tmp/{tmp_folder_name}/{tmp_file_name}'
            logger.info('For this purpose, temporary file name is %r', tmp_full_name)
            # Clean up container's temporary folder
            self.run_command('rm -rf /tmp/{0}; mkdir -p /tmp/{0}'.format(tmp_folder_name))
            # Create/Clean up the host's temporary folder
            self.run_command(
                'rm -rf /tmp/{0}; mkdir -p /tmp/{0}'.format(tmp_folder_name), ensure_host=True)
            # Now copy the file in container to the tmp folder
            assert self.run_command(f'cp {remote_file} {tmp_full_name}')
            # Use the oc rsync to pull the file onto the host
            rsync_cmd = 'oc rsync --namespace={proj} {pod}:/tmp/{file} /tmp'
            assert self.run_command(rsync_cmd.format(proj=self._project, pod=self._container,
                                                     file=tmp_folder_name),
                                    ensure_host=True)
            # Now download the file to the openshift host
            scp = SCPClient(self.get_transport(), progress=self._progress_callback).get(
                tmp_full_name, local_path, **kwargs)
            check_call([
                'mv',
                os_path.join(local_path, tmp_file_name),
                os_path.join(local_path, base_name)])
            return scp
        else:
            return SCPClient(self.get_transport(), progress=self._progress_callback).get(
                remote_file, local_path, **kwargs)

    def patch_file(self, local_path, remote_path, md5=None):
        """ Patches a single file on the appliance

        Args:
            local_path: Path to patch (diff) file
            remote_path: Path to file to be patched (on the appliance)
            md5: MD5 checksum of the original file to check if it has changed

        Returns:
            True if changes were applied, False if patching was not necessary

        Note:
            If there is a .bak file present and the file-to-be-patched was
            not patched by the current patch-file, it will be used to restore it first.
            Recompiling assets and restarting appropriate services might be required.
        """
        logger.info('Patching %s', remote_path)

        # Upload diff to the appliance
        diff_remote_path = os_path.join('/tmp/', os_path.basename(remote_path))
        self.put_file(local_path, diff_remote_path)

        # If already patched with current file, exit
        logger.info('Checking if already patched')
        result = self.run_command(
            f'patch {remote_path} {diff_remote_path} -f --dry-run -R')
        if result.success:
            return False

        # If we have a .bak file available, it means the file is already patched
        # by some older patch; in that case, replace the file-to-be-patched by the .bak first
        logger.info("Checking if %s.bak is available", remote_path)
        result = self.run_command(f'test -e {remote_path}.bak')
        if result.success:
            logger.info("%s.bak found; using it to replace %s", remote_path, remote_path)
            result = self.run_command(f'mv {remote_path}.bak {remote_path}')
            if result.failed:
                raise Exception(
                    f"Unable to replace {remote_path} with {remote_path}.bak")
        else:
            logger.info("%s.bak not found", remote_path)

        # If not patched and there's MD5 checksum available, check it
        if md5:
            logger.info("MD5 sum check in progress for %s", remote_path)
            result = self.run_command(f'md5sum -c - <<< "{md5} {remote_path}"')
            if result.success:
                logger.info('MD5 sum check result: file not changed')
            else:
                logger.warning('MD5 sum check result: file has been changed!')

        # Create the backup and patch
        result = self.run_command(
            f'patch {remote_path} {diff_remote_path} -f -b -z .bak')
        if result.failed:
            raise Exception(f"Unable to patch file {remote_path}: {result.output}")
        return True

    def is_file_available(self, remote_path):
        """Check file available or not on remote host

        Args:
            remote_path: Path to remote file

        Returns:
            True if file available else False
        """
        files = self.run_command(f"ls {os_path.dirname(remote_path)}").output
        return os_path.basename(remote_path) in files

    def remove_file(self, remote_path, force=True, recursive=False):
        """Remove file from remote host

        Args:
            remote_path: Path to remote file
            force: add -f to rm args
            recursive: add -r to rm args
        """
        if self.is_file_available(remote_path):
            opts = []
            if force:
                opts.append('-f')
            if recursive:
                opts.append('-r')
            args = ' '.join(opts)
            self.run_command(f"rm {args} {remote_path}")

    def get_build_datetime(self):
        command = "stat --printf=%Y /var/www/miq/vmdb/VERSION"
        return parsetime.fromtimestamp(int(self.run_command(command).output.strip()))

    def get_build_date(self):
        return self.get_build_datetime().date()

    def is_appliance_downstream(self):
        return self.run_command("stat /var/www/miq/vmdb/BUILD").success

    def uptime(self):
        out = self.run_command('cat /proc/uptime').output
        match = re.findall(r'\d+\.\d+', out)

        if match:
            return float(match[0])

        return 0

    def client_address(self):
        res = self.run_command('echo $SSH_CLIENT', ensure_host=True, ensure_user=True)
        # SSH_CLIENT format is 'clientip clientport serverport', we want clientip
        if not res.output:
            raise Exception('unable to get client address via SSH')
        return res.output.split()[0]

    def appliance_has_netapp(self):
        return self.run_command("stat /var/www/miq/vmdb/HAS_NETAPP").success

    @property
    def status(self):
        """Parses the output of the ``systemctl status evmserverd``.

        Returns:
            A dictionary containing ``servers`` and ``workers``, both lists. Each of the lists
            contains dictionaries, one per line. You can refer inside the dictionary using the
            headers.
        """
        matcher = re.compile(
            '|'.join([
                'DEPRECATION WARNING',
                'called from block in',
                'Please use .* instead',
                'key :terminate is duplicated and overwritten',
                r'--------\+--',
                'Checking EVM status...'
            ]))
        data = self.run_rake_command("evm:status")
        if data.rc != 0:
            raise Exception(f"systemctl status evmserverd $?={data.rc}")
        data = data.output.strip().split("\n\n")
        if len(data) == 2:
            srvs, wrks = data
        else:
            srvs = data[0]
            wrks = ""
        if "checking evm status" not in srvs.lower():
            raise Exception(f"Wrong command output:\n{data.output}")

        def _process_dict(d):
            for k in ['ID', 'PID', 'SPID']:
                try:
                    d[k] = int(d[k])
                except ValueError:
                    d[k] = None
                except KeyError:
                    continue

            if "Active Roles" in d:
                d["Active Roles"] = set(d["Active Roles"].split(":"))
            if "Last Heartbeat" in d:
                d["Last Heartbeat"] = iso8601.parse_date(d["Last Heartbeat"])
            if "Started On" in d:
                d["Started On"] = iso8601.parse_date(d["Started On"])

        # Servers part
        srvs = [line for line in srvs.split("\n")[1:] if matcher.search(line) is None]
        srv_headers = [h.strip() for h in srvs[0].strip().split("|")]
        srv_body = srvs[1:]
        servers = []
        for server in srv_body:
            fields = [f.strip() for f in server.strip().split("|")]
            srv = dict(list(zip(srv_headers, fields)))
            _process_dict(srv)
            servers.append(srv)

        # Workers part
        # TODO: Figure more permanent solution for ignoring the warnings
        wrks = [line for line in wrks.split("\n") if matcher.search(line) is None]

        workers = []
        if wrks:
            wrk_headers = [h.strip() for h in wrks[0].strip().split("|")]
            wrk_body = wrks[2:]
            for worker in wrk_body:
                fields = [f.strip() for f in worker.strip().split("|")]
                wrk = dict(list(zip(wrk_headers, fields)))
                _process_dict(wrk)
                # ansible worker doesn't work in pod in 5.8
                if (wrk['Worker Type'] == 'EmbeddedAnsibleWorker' and
                        "5.8" in self.vmdb_version and
                        self.run_command('[[ -f Dockerfile ]]').success):
                    continue
                workers.append(wrk)
        return {"servers": servers, "workers": workers}


class SSHTail(SSHClient):

    def __init__(self, remote_filename, **connect_kwargs):
        super().__init__(stream_output=False, **connect_kwargs)
        self._remote_filename = remote_filename
        self._sftp_client = None
        self._remote_file_size = None

    def __iter__(self):
        for line in self.raw_lines():
            yield line.rstrip()

    def raw_lines(self):
        with self as sshtail:
            fstat = sshtail._sftp_client.stat(self._remote_filename)
            if self._remote_file_size is not None:
                if self._remote_file_size < fstat.st_size:
                    remote_file = self._sftp_client.open(self._remote_filename, 'r')
                    remote_file.seek(self._remote_file_size, 0)
                    while (remote_file.tell() < fstat.st_size):
                        line = remote_file.readline()  # Note the  missing rstrip() here!
                        yield line
            self._remote_file_size = fstat.st_size

    def raw_string(self):
        return ''.join(self)

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

    def lines_as_list(self):
        """Return lines as list"""
        return list(self)


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
        f.write("{} {} {}\n".format(pub.get_name(), pub.get_base64(),
            'autogenerated cfme_tests key'))


def unquirked_ssh_client(**kwargs):
    """ A factory for the SSHClient dealing with some of its quirks:

    * When hostname is None, the SSHClient will connect to the default
      appliance.
    * Set use_check_port to False to disable waiting for port being
      available in the SSHClient.
    * The SSHClient does not connect in the object creation time.
    """
    if kwargs['hostname'] is None:
        raise ValueError('The hostname argument cannot be None!')
    client = SSHClient(use_check_port=False, **kwargs)
    client.connect()
    return client


def connect_ssh(vm: Vm, creds: 'Credential',
                num_sec=CONNECT_RETRIES_TIMEOUT,
                connect_timeout=CONNECT_TIMEOUT,
                delay=CONNECT_SSH_DELAY):
    """
    This function attempts to connect all the IPs of the vm in several
    round. After each round it will delay an amount of seconds specified as
    `delay`. Once connective IP is found, it will return connected SSHClient.
    The `connect_timeout` specifies a timeout for each connection attempt.
    """

    def connection_factory(ip):
        return unquirked_ssh_client(
            hostname=ip,
            username=creds.principal, password=creds.secret,
            timeout=connect_timeout)

    msg = "The num_sec is smaller then connect_timeout. This looks like a bug."
    assert num_sec > connect_timeout, msg

    return retry_connect(lambda: vm.all_ips, connection_factory, num_sec=num_sec, delay=delay)
