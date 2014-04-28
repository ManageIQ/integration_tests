import socket

from utils.conf import cfme_data


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
    address = (cfme_data['ip_echo']['host'], int(cfme_data['ip_echo']['port']))
    cxn = socket.create_connection(address)
    my_ip_address = cxn.recv(1024)
    cxn.close()
    return my_ip_address.strip()


def ip_echo_socket(port=32123):
    """A simple socket server, for use with :py:func:`my_ip_address`"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', port))
    s.listen(0)
    while True:
        conn, addr = s.accept()
        conn.sendall(addr[0])
        conn.close()
