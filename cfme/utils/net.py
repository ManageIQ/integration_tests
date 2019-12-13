import os
import re
import socket
from collections import defaultdict

from cfme.fixtures.pytest_store import store
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

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
    with socket.socket(socket.AF_INET, socktype) as s:
        s.bind(('', 0))
        addr, port = s.getsockname()
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
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
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
        addr = store.current_appliance.hostname
    if port not in _ports[addr] or force:
        # First try DNS resolution
        try:
            addr_info = socket.getaddrinfo(addr, port)[0]
            sockaddr = addr_info[4]
            addr = sockaddr[0]
            # Then try to connect to the port
            try:
                socket.create_connection((addr, port), timeout=10).close()  # immediately close
            except socket.error:
                _ports[addr][port] = False
            else:
                _ports[addr][port] = True
        except Exception:
            _ports[addr][port] = False
    return _ports[addr][port]


def net_check_remote(port, addr=None, machine_addr=None, ssh_creds=None, force=False):
    """Checks the availability of a port from outside using another machine (over SSH)"""
    from cfme.utils.ssh import SSHClient
    port = int(port)
    if not addr:
        addr = my_ip_address()
    if port not in _ports[addr] or force:
        if not machine_addr:
            machine_addr = store.current_appliance.hostname
        if not ssh_creds:
            ssh_client = store.current_appliance.ssh_client
        else:
            ssh_client = SSHClient(
                hostname=machine_addr,
                username=ssh_creds['username'],
                password=ssh_creds['password']
            )
        with ssh_client:
            # on exception => fails with return code 1
            cmd = '''python2 -c "
import sys, socket
addr = socket.gethostbyname('%s')
socket.create_connection((addr, %d), timeout=10)
sys.exit(0)
            "''' % (addr, port)
            result = ssh_client.run_command(cmd)
            _ports[addr][port] = result.success
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
        logger.info('Pinging address: %s', ip_addr)
        status = os.system("ping -c1 -w2 {} >/dev/null".format(ip_addr))
        if status == 0:
            logger.info('IP: %s is RESPONDING !', ip_addr)
            return True
        logger.info('ping exit status: %d, IP: %s is UNREACHABLE !', status, ip_addr)
        return False
    except Exception as e:
        logger.exception(e)
        return False


def find_pingable(mgmt_vm, allow_ipv6=True):
    """Looks for a pingable address from mgmt_vm.all_ips

     Assuming mgmt_vm is a wrapanapi VM entity, with all_ips and ip methods

     Returns:
         In priority: first pingable address, address 'selected' by wrapanapi (possibly None)
     """
    for ip in getattr(mgmt_vm, 'all_ips', []):
        if ip:
            if not allow_ipv6 and is_ipv6(ip):
                logger.debug('VMs ip is ipv6, skipping it: %s', ip)
                continue
            if not is_pingable(ip):
                logger.debug('Could not reach mgmt IP on VM: %s', ip)
                continue

            logger.info('Found reachable IP for VM: %s', ip)
            return ip

    else:
        logger.info('No reachable IPs found for VM, just returning wrapanapi IP')
        return getattr(mgmt_vm, 'ip', None)


def find_pingable_ipv6(mgmt_vm):
    """Looks for a pingable ipv6 address from mgmt_vm.all_ips

     Assuming mgmt_vm is a wrapanapi VM entity, with all_ips and ip methods

     Returns:
         In priority: first pingable ipv6 address, address 'selected' by wrapanapi (possibly None)
     """
    for ip in getattr(mgmt_vm, 'all_ips', []):
        if not is_ipv6(ip) or not is_pingable(ip):
            logger.debug(f"Could not reach mgmt IP on VM: {ip}")
            continue

        logger.info(f"'Found reachable IP for VM: {ip}")
        return ip

    else:
        logger.info("No reachable IPv6s found for VM")
        return None


def wait_pingable(mgmt_vm, wait=30, allow_ipv6=True):
    """Looks for a pingable address from mgmt_vm.all_ips and waits if it isn't present

     Assuming mgmt_vm is a wrapanapi VM entity, with all_ips and ip methods

     Returns:
         first pingable address or exception
    """
    def is_reachable(mgmt_vm):
        ip = find_pingable(mgmt_vm, allow_ipv6=allow_ipv6)
        # above method returns ip from wrapanapi if there is no suitable ip.
        # this ip can be ipv6 one and pingable but it isn't acceptable for sprout
        if is_pingable(ip) and not (not allow_ipv6 and is_ipv6(ip)):
            return ip
        else:
            return None

    return wait_for(
        is_reachable,
        func_args=[mgmt_vm],
        fail_condition=None,
        delay=5,
        num_sec=wait
    )[0]


def is_ipv4(ip_addr):
    """verifies whether address is ipv4.

    Args:
        ip_addr: ip_address to verify.
    returns: return True if ip_address is ipv4 else returns False.
    """
    try:
        socket.inet_pton(socket.AF_INET, ip_addr)
    except AttributeError:
        try:
            socket.inet_aton(ip_addr)
        except socket.error:
            return False
        return ip_addr.count('.') == 3
    except socket.error:
        return False

    return True


def is_ipv6(ip_addr):
    """verifies whether address is ipv6.

    Args:
        ip_addr: ip_address to verify.
    returns: return True if ip_address is ipv6 else returns False.
    """
    try:
        socket.inet_pton(socket.AF_INET6, ip_addr)
    except socket.error:
        return False

    return True
