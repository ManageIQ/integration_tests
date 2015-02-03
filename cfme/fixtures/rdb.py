"""Rdb: Remote debugger

Given the following configuration in conf/rdb.yaml::

    breakpoints:
      - subject: Brief explanation of a problem
        exceptions:
          - cfme.exceptions.ImportableExampleException
        recipients:
          - user@example.com

Any time an exception listed in a breakpoint's "exceptions" list is raised in :py:func:`rdb_catch`
context in the course of a test run, a remote debugger will be started on a random port, and the
users listed in "recipients" will be emailed instructions to access the remote debugger via telnet.

By default, Rdb assumes that there is a working MTA available on localhost, but this can
be configured in ``conf['env']['smtp']['server']``.

Note:

    This is very insecure, and should be used as a last resort for debugging elusive failures.

"""

import os
import pdb
import smtplib
import socket
import sys
from contextlib import contextmanager
from email.mime.text import MIMEText
from importlib import import_module
from textwrap import dedent
from urlparse import urlparse

from fixtures.pytest_store import store, write_line
from utils import conf
from utils.log import logger

_breakpoint_exceptions = {}

# defaults
smtp_conf = {
    'server': 'localhost'
}
# Update defaults from conf
smtp_conf.update(conf.env.get('smtp', {}))


for breakpoint in conf.rdb.get('breakpoints', []):
    for i, exc_name in enumerate(breakpoint['exceptions']):
        split_exc = exc_name.rsplit('.', 1)
        exc = getattr(import_module(split_exc[0]), split_exc[1])
        # stash exceptions for easy matching in exception handlers
        _breakpoint_exceptions[exc] = breakpoint


class Rdb(pdb.Pdb):
    """Remote Debugger

    When set_trace is called, it will open a socket on a random unprivileged port connected to a
    Pdb debugging session. This session can be accessed via telnet, and will end when "continue"
    is called in the Pdb session.

    """
    def __init__(self):
        self._stdout = sys.stdout
        self._stdin = sys.stdin
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # bind to random port
        self.sock.bind(('0.0.0.0', 0))

    def do_continue(self, arg):
        sys.stdout = self._stdout
        sys.stdin = self._stdin
        self.sock.close()
        self.set_continue()
        return 1
    do_c = do_cont = do_continue

    def set_trace(self, *args, **kwargs):
        host, port = self.sock.getsockname()
        msg = 'Remote debugger listening on TCP {}'.format(port)
        logger.error(msg)
        write_line(msg)
        self.sock.listen(1)
        (client_socket, address) = self.sock.accept()
        client_fh = client_socket.makefile('rw')
        pdb.Pdb.__init__(self, completekey='tab', stdin=client_fh, stdout=client_fh)
        sys.stdout = sys.stdin = client_fh
        pdb.Pdb.set_trace(self, *args, **kwargs)


def pytest_addoption(parser):
    group = parser.getgroup('cfme')
    group.addoption('--rdb', dest='userdb', action='store_true', default=False,
        help="Enable remote debugging")


@contextmanager
def rdb_catch():
    """Context Manager used to wrap mysterious failures for remote debugging."""
    if store.config and store.config.option.userdb:
        try:
            yield
        except Exception as exc:
            # Set up the remote debugger when we see one of our breakpoint exceptions
            if type(exc) in _breakpoint_exceptions:
                breakpoint = _breakpoint_exceptions[exc]
            else:
                raise

            rdb = Rdb()
            host, port = rdb.sock.getsockname()

            # Try to guess a hostname based on jenkins env, otherwise just list the port
            if os.environ.get('JENKINS_URL'):
                parsed = urlparse(os.environ['JENKINS_URL'])
                endpoint = 'host {} port {}'.format(parsed.hostname, port)
            else:
                endpoint = 'pytest runner port {}'.format(port)

            # write and send an email
            subject = 'RDB Breakpoint: {}'.format(breakpoint['subject'])
            body = dedent("""\
            A py.test run encountered an error. The remote debugger is running
            on {} (TCP), waiting for telnet connection.
            """).format(endpoint)
            smtp = smtplib.SMTP(smtp_conf['server'])
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['To'] = ', '.join(breakpoint['recipients'])

            smtp.sendmail('no-reply@example.com', breakpoint['recipients'], msg.as_string())
            rdb.set_trace()
    else:
        yield
