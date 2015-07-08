"""Rdb: Remote debugger

Given the following configuration in conf/rdb.yaml::

    breakpoints:
      - subject: Brief explanation of a problem
        exceptions:
          - cfme.exceptions.ImportableExampleException
          - BuiltinException (e.g. ValueError)
        recipients:
          - user@example.com

Any time an exception listed in a breakpoint's "exceptions" list is raised in :py:func:`rdb_catch`
context in the course of a test run, a remote debugger will be started on a random port, and the
users listed in "recipients" will be emailed instructions to access the remote debugger via telnet.

The exceptions will be imported, so their fully-qualified importable path is required.
Exceptions without a module path are assumed to be builtins.

An Rdb instance can be used just like a :py:class:`Pdb <python:Pdb>` instance.

Additionally, a signal handler has been set up to allow for triggering Rdb during a test run. To
invoke it, ``kill -USR1`` a test-running process and Rdb will start up. No emails are sent when
operating in this mode, so check the py.test console for the endpoint address.

By default, Rdb assumes that there is a working MTA available on localhost, but this can
be configured in ``conf['env']['smtp']['server']``.

Note:

    This is very insecure, and should be used as a last resort for debugging elusive failures.

"""
import signal
import smtplib
import socket
import sys
from contextlib import contextmanager
from email.mime.text import MIMEText
from importlib import import_module
from pdb import Pdb
from textwrap import dedent

from fixtures.pytest_store import store, write_line
from utils import conf
from utils.log import logger

_breakpoint_exceptions = {}

# defaults
smtp_conf = {
    'server': '127.0.0.1'
}
# Update defaults from conf
smtp_conf.update(conf.env.get('smtp', {}))


for breakpoint in (conf.rdb.get('breakpoints') or []):
    for i, exc_name in enumerate(breakpoint['exceptions']):
        split_exc = exc_name.rsplit('.', 1)
        if len(split_exc) == 1:
            # If no module is given to import from, assume builtin
            split_exc = ['__builtin__', exc_name]
        exc = getattr(import_module(split_exc[0]), split_exc[1])
        # stash exceptions for easy matching in exception handlers
        _breakpoint_exceptions[exc] = breakpoint


def rdb_handle_signal(signal, frame):
    # only registered for USR1, no need to inspect the signal,
    # just hand the frame off to Rdb
    Rdb('Debugger started on user signal').set_trace(frame)
signal.signal(signal.SIGUSR1, rdb_handle_signal)


# XXX: Pdb (and its bases) are old-style classobjs, so don't use super
class Rdb(Pdb):
    """Remote Debugger

    When set_trace is called, it will open a socket on a random unprivileged port connected to a
    Pdb debugging session. This session can be accessed via telnet, and will end when "continue"
    is called in the Pdb session.

    """
    def __init__(self, prompt_msg=''):
        self._prompt_msg = str(prompt_msg)
        self._stdout = sys.stdout
        self._stdin = sys.stdin
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # bind to random port
        self.sock.bind(('0.0.0.0', 0))

    def do_continue(self, arg):
        sys.stdout = self._stdout
        sys.stdin = self._stdin
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        self.set_continue()
        return 1
    do_c = do_cont = do_continue

    def interaction(self, *args, **kwargs):
        print >>self.stdout, self._prompt_msg
        Pdb.interaction(self, *args, **kwargs)

    def set_trace(self, *args, **kwargs):
        """Start a pdb debugger available via telnet, and optionally email people the endpoint

        The endpoint will always be seen in the py.test runner output.

        Keyword Args:
            recipients: A list where, if set, an email will be sent to email addresses
                in this list.
            subject: If set, an optional custom email subject

        """
        host, port = self.sock.getsockname()
        endpoint = 'host {} port {}'.format(store.my_ip_address, port)

        recipients = kwargs.pop('recipients', None)
        if recipients:
            # write and send an email
            subject = kwargs.pop('subject', 'RDB Breakpoint: Manually invoked')
            body = dedent("""\
            A py.test run encountered an error. The remote debugger is running
            on {} (TCP), waiting for telnet connection.
            """).format(endpoint)

            try:
                smtp_server = smtp_conf['server']
                smtp = smtplib.SMTP(smtp_server)
                msg = MIMEText(body)
                msg['Subject'] = subject
                msg['To'] = ', '.join(recipients)
                smtp.sendmail('rdb-breakpoint@example.com', recipients, msg.as_string())
            except socket.error:
                logger.critical("Couldn't send email")

        msg = 'Remote debugger listening on {}'.format(endpoint)
        logger.critical(msg)
        write_line(msg, red=True, bold=True)
        self.sock.listen(1)
        (client_socket, address) = self.sock.accept()
        client_fh = client_socket.makefile('rw')
        Pdb.__init__(self, completekey='tab', stdin=client_fh, stdout=client_fh)
        sys.stdout = sys.stdin = client_fh
        Pdb.set_trace(self, *args, **kwargs)
        msg = 'Debugger on {} shut down'.format(endpoint)
        logger.critical(msg)
        write_line(msg, green=True, bold=True)


def send_breakpoint_email(exctype, msg=''):
    breakpoint = _breakpoint_exceptions[exctype]
    subject = 'RDB Breakpoint: {}'.format(breakpoint['subject'])
    rdb = Rdb(msg)
    rdb.set_trace(subject=subject, recipients=breakpoint['recipients'])


def pytest_internalerror(excrepr, excinfo):
    if excinfo.type in _breakpoint_exceptions:
        msg = "A py.test internal error has triggered RDB:\n"
        msg += str(excrepr)
        send_breakpoint_email(excinfo.type, msg)


@contextmanager
def rdb_catch():
    """Context Manager used to wrap mysterious failures for remote debugging."""
    try:
        yield
    except tuple(_breakpoint_exceptions) as exc:
        send_breakpoint_email(type(exc))
