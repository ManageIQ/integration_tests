# -*- coding: utf-8 -*-
import iso8601
import re
import socket
import sys
from collections import namedtuple
from os import path as os_path
from urlparse import urlparse

import paramiko
from scp import SCPClient
import diaper

from utils import conf, ports, version
from utils.log import logger
from utils.net import net_check
from fixtures.pytest_store import store
from utils.path import project_path
from utils.timeutil import parsetime


# Default blocking time before giving up on an ssh command execution,
# in seconds (float)
RUNCMD_TIMEOUT = 1200.0
SSHResult = namedtuple("SSHResult", ["rc", "output"])

_ssh_key_file = project_path.join('.generated_ssh_key')
_ssh_pubkey_file = project_path.join('.generated_ssh_key.pub')

_client_session = []


class SSHClient(paramiko.SSHClient):
    """paramiko.SSHClient wrapper

    Allows copying/overriding and use as a context manager
    Constructor kwargs are handed directly to paramiko.SSHClient.connect()
    """
    def __init__(self, stream_output=False, **connect_kwargs):
        super(SSHClient, self).__init__()
        self._streaming = stream_output
        # deprecated/useless karg, included for backward-compat
        self._keystate = connect_kwargs.pop('keystate', None)

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

        default_connect_kwargs["port"] = ports.SSH

        # Overlay defaults with any passed-in kwargs and store
        default_connect_kwargs.update(connect_kwargs)
        self._connect_kwargs = default_connect_kwargs
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        _client_session.append(self)

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
        sent_percent = (sent * 100.) / size
        if sent_percent > 0:
            logger.debug('%s scp progress: %f%% ', filename, sent_percent)

    def close(self):
        with diaper:
            _client_session.remove(self)
        super(SSHClient, self).close()

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
            return super(SSHClient, self).connect(**self._connect_kwargs)

    def open_sftp(self, *args, **kwargs):
        self.connect()
        return super(SSHClient, self).open_sftp(*args, **kwargs)

    def get_transport(self, *args, **kwargs):
        if self.connected:
            logger.trace('reusing ssh transport')
        else:
            logger.trace('connecting new ssh transport')
            self.connect()
        return super(SSHClient, self).get_transport(*args, **kwargs)

    def run_command(self, command, timeout=RUNCMD_TIMEOUT, reraise=False):
        if isinstance(command, dict):
            command = version.pick(command)
        logger.info("Running command `%s`", command)
        template = '{}\n'
        command = template.format(command)

        output = ''
        try:
            session = self.get_transport().open_session()
            if timeout:
                session.settimeout(float(timeout))
            session.exec_command(command)
            stdout = session.makefile()
            stderr = session.makefile_stderr()
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
            if reraise:
                raise
            else:
                logger.exception(exc)
        except socket.timeout as e:
            logger.error("Command `%s` timed out.", command)
            logger.exception(e)
            logger.error("Output of the command before it failed was:\n%s", output)
            raise

        # Returning two things so tuple unpacking the return works even if the ssh client fails
        return SSHResult(1, None)

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

    def run_rails_command(self, command, timeout=RUNCMD_TIMEOUT):
        logger.info("Running rails command `%s`", command)
        return self.run_command('cd /var/www/miq/vmdb; bin/rails runner {}'.format(command),
            timeout=timeout)

    def run_rake_command(self, command, timeout=RUNCMD_TIMEOUT):
        logger.info("Running rake command `%s`", command)
        return self.run_command('cd /var/www/miq/vmdb; bin/rake {}'.format(command),
            timeout=timeout)

    def put_file(self, local_file, remote_file='.', **kwargs):
        logger.info("Transferring local file %s to remote %s", local_file, remote_file)
        return SCPClient(self.get_transport(), progress=self._progress_callback).put(
            local_file, remote_file, **kwargs)

    def get_file(self, remote_file, local_path='', **kwargs):
        logger.info("Transferring remote file %s to local %s", remote_file, local_path)
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
        rc, out = self.run_command(
            'patch {} {} -f --dry-run -R'.format(remote_path, diff_remote_path))
        if rc == 0:
            return False

        # If we have a .bak file available, it means the file is already patched
        # by some older patch; in that case, replace the file-to-be-patched by the .bak first
        logger.info("Checking if {}.bak is available".format(remote_path))
        rc, out = self.run_command('test -e {}.bak'.format(remote_path))
        if rc == 0:
            logger.info(
                "{}.bak found; using it to replace {}".format(remote_path, remote_path))
            rc, out = self.run_command('mv {}.bak {}'.format(remote_path, remote_path))
            if rc != 0:
                raise Exception(
                    "Unable to replace {} with {}.bak".format(remote_path, remote_path))
        else:
            logger.info("{}.bak not found".format(remote_path))

        # If not patched and there's MD5 checksum available, check it
        if md5:
            logger.info("MD5 sum check in progress for %s", remote_path)
            rc, out = self.run_command('md5sum -c - <<< "{} {}"'.format(md5, remote_path))
            if rc == 0:
                logger.info('MD5 sum check result: file not changed')
            else:
                logger.warning('MD5 sum check result: file has been changed!')

        # Create the backup and patch
        rc, out = self.run_command(
            'patch {} {} -f -b -z .bak'.format(remote_path, diff_remote_path))
        if rc != 0:
            raise Exception("Unable to patch file {}: {}".format(remote_path, out))
        return True

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
        if not res.output:
            raise Exception('unable to get client address via SSH')
        return res.output.split()[0]

    def appliance_has_netapp(self):
        return self.run_command("stat /var/www/miq/vmdb/HAS_NETAPP").rc == 0

    @property
    def status(self):
        """Parses the output of the ``service evmserverd status``.

        Returns:
            A dictionary containing ``servers`` and ``workers``, both lists. Each of the lists
            contains dictionaries, one per line. You can refer inside the dictionary using the
            headers.
        """
        if version.current_version() < "5.5":
            data = self.run_command("service evmserverd status")
        else:
            data = self.run_rake_command("evm:status")
        if data.rc != 0:
            raise Exception("service evmserverd status $?={}".format(data.rc))
        data = data.output.strip().split("\n\n")
        if len(data) == 2:
            srvs, wrks = data
        else:
            srvs = data[0]
            wrks = ""
        if "checking evm status" not in srvs.lower():
            raise Exception("Wrong command output:\n{}".format(data.output))

        def _process_dict(d):
            d["PID"] = int(d["PID"])
            d["ID"] = int(d["ID"])
            try:
                d["SPID"] = int(d["SPID"])
            except ValueError:
                d["SPID"] = None
            if "Active Roles" in d:
                d["Active Roles"] = set(d["Active Roles"].split(":"))
            if "Last Heartbeat" in d:
                d["Last Heartbeat"] = iso8601.parse_date(d["Last Heartbeat"])
            if "Started On" in d:
                d["Started On"] = iso8601.parse_date(d["Started On"])

        # Servers part
        srvs = srvs.split("\n")[1:]
        srv_headers = [h.strip() for h in srvs[0].strip().split("|")]
        srv_body = srvs[2:]
        servers = []
        for server in srv_body:
            fields = [f.strip() for f in server.strip().split("|")]
            srv = dict(zip(srv_headers, fields))
            _process_dict(srv)
            servers.append(srv)

        # Workers part
        wrks = wrks.split("\n")
        wrk_headers = [h.strip() for h in wrks[0].strip().split("|")]
        wrk_body = wrks[2:]
        workers = []
        for worker in wrk_body:
            fields = [f.strip() for f in worker.strip().split("|")]
            wrk = dict(zip(wrk_headers, fields))
            _process_dict(wrk)
            workers.append(wrk)
        return {"servers": servers, "workers": workers}


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
        f.write("{} {} {}\n".format(pub.get_name(), pub.get_base64(),
            'autogenerated cfme_tests key'))
