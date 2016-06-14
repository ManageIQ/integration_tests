from collections import defaultdict
import socket
import os
import re
import urlparse
from fixtures.pytest_store import store

from utils.log import logger

_ports = defaultdict(dict)
_dns_cache = {}
ip_address = re.compile(
    r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")


def random_port(tcp=True):
    """Get a random port number for making a socket

    Args:
        tcp: Return a TCP port number if True, UDP if False

    This may not be reliable at all due to an inherent race condition. This works
    by creating a socket on an ephemeral port, inspecting it to see what port was used,
    closing it, and returning that port number. In the time between closing the socket
    and opening a new one, it's possible for the OS to reopen that port for another purpose.

    In practical testing, this race condition did not result in a failure to (re)open the
    returned port number, making this solution squarely "good enough for now".
    """
    # Port 0 will allocate an ephemeral port
    socktype = socket.SOCK_STREAM if tcp else socket.SOCK_DGRAM
    s = socket.socket(socket.AF_INET, socktype)
    s.bind(('', 0))
    addr, port = s.getsockname()
    s.close()
    return port


def my_ip_address(http=False):
    """Get the ip address of the host running tests using the service listed in cfme_data['ip_echo']

    The ip echo endpoint is expected to write the ip address to the socket and close the
    connection. See a working example of this in :py:func:`ip_echo_socket`.

    """
    # the pytest store does this work, it's included here for convenience
    return store.my_ip_address


def ip_echo_socket(port=32123):
    """A simple socket server, for use with :py:func:`my_ip_address`"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', port))
    s.listen(0)
    while True:
        conn, addr = s.accept()
        conn.sendall(addr[0])
        conn.close()


def net_check(port, addr=None, force=False):
    """Checks the availablility of a port"""
    port = int(port)
    if not addr:
        addr = urlparse.urlparse(store.base_url).hostname
    if port not in _ports[addr] or force:
        # First try DNS resolution
        try:
            addr = socket.gethostbyname(addr)

            # Then try to connect to the port
            try:
                socket.create_connection((addr, port), timeout=10)
                _ports[addr][port] = True
            except socket.error:
                _ports[addr][port] = False
        except:
            _ports[addr][port] = False
    return _ports[addr][port]


def net_check_remote(port, addr=None, machine_addr=None, ssh_creds=None, force=False):
    """Checks the availability of a port from outside using another machine (over SSH)"""
    from utils.ssh import SSHClient
    port = int(port)
    if not addr:
        addr = my_ip_address()
    if port not in _ports[addr] or force:
        if not machine_addr:
            machine_addr = urlparse.urlparse(store.base_url).hostname
        if not ssh_creds:
            ssh = SSHClient(hostname=machine_addr)
        else:
            ssh = SSHClient(
                hostname=machine_addr,
                username=ssh_creds['username'],
                password=ssh_creds['password']
            )
        with ssh:
            # on exception => fails with return code 1
            cmd = '''python -c "
import sys, socket
addr = socket.gethostbyname('%s')
socket.create_connection((addr, %d), timeout=10)
sys.exit(0)
            "''' % (addr, port)
            ret, out = ssh.run_command(cmd)
            if ret == 0:
                _ports[addr][port] = True
            else:
                _ports[addr][port] = False
    return _ports[addr][port]


def resolve_hostname(hostname, force=False):
    """Cached DNS resolver. If the hostname does not resolve to an IP, returns None."""
    if hostname not in _dns_cache or force:
        try:
            _dns_cache[hostname] = socket.gethostbyname(hostname)
        except socket.gaierror:
            _dns_cache[hostname] = None
    return _dns_cache[hostname]


def resolve_ips(host_iterable, force_dns=False):
    """Takes list of hostnames, ips and another things. If the item is not an IP, it will be tried
    to be converted to an IP. If that succeeds, it is appended to the set together with original
    hostname. If it can't be resolved, just the original hostname is appended.
    """
    result = set([])
    for host in map(str, host_iterable):
        result.add(host)  # It is already an  IP address
        if ip_address.match(host) is None:
            ip = resolve_hostname(host, force=force_dns)
            if ip is not None:
                result.add(ip)
    return result


def is_pingable(ip_addr):
    """verifies the specified ip_address is reachable or not.

    Args:
        ip_addr: ip_address to verify the PING.
    returns: return True is ip_address is pinging else returns False.
    """
    try:
        status = os.system("ping -c1 -w2 {}".format(ip_addr))
        if status == 0:
            logger.info('IP: %s is UP !', ip_addr)
            return True
        logger.info('IP: %s is DOWN !', ip_addr)
        return False
    except Exception as e:
        logger.exception(e)
        return False
