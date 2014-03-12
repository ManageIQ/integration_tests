#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""This module provides a fixture useful for checking the e-mails arrived.

Main use is of fixture :py:meth:`smtp_test`, which is function scoped. There is also
a :py:meth:`smtp_test_module` fixture for which the smtp_test is just a function-scoped wrapper
to speed things up. The base of all this is the session-scoped _smtp_test_session that keeps care
about the collector.
"""
import pytest
import signal
import subprocess
import time

from cfme.configure import configuration
from utils.log import create_logger
from utils.net import random_port, my_ip_address
from utils.path import scripts_path
from utils.smtp_collector_client import SMTPCollectorClient


logger = create_logger('emails')


@pytest.yield_fixture(scope="session")
def _smtp_test_session(request):
    """Fixture, which prepares the appliance for e-mail capturing tests

    Returns: :py:class:`util.smtp_collector_client.SMTPCollectorClient` instance.
    """
    logger.info("Preparing start for e-mail collector")
    mail_server_port = random_port()
    mail_query_port = random_port()
    my_ip = my_ip_address()
    logger.info("Mind that it needs ports %d and %d open" % (mail_query_port, mail_server_port))
    smtp_conf = configuration.SMTPSettings(
        host=my_ip,
        port=mail_server_port,
        auth="none",
    )
    smtp_conf.update()
    server_filename = scripts_path.join('smtp_collector.py').strpath
    server_command = server_filename + " --smtp-port %d --query-port %d" % (
        mail_server_port,
        mail_query_port
    )
    logger.info("Starting mail collector %s" % server_command)
    collector = subprocess.Popen(server_command, shell=True)
    logger.info("Collector pid %d" % collector.pid)
    logger.info("Waiting for collector to become alive.")
    time.sleep(3)
    assert collector.poll() is None, "Collector has died. Something must be blocking selected ports"
    logger.info("Collector alive")
    client = SMTPCollectorClient(
        my_ip,
        mail_query_port
    )
    yield client
    logger.info("Sending KeyboardInterrupt to collector")
    collector.send_signal(signal.SIGINT)
    collector.wait()
    logger.info("Collector finished")


@pytest.yield_fixture(scope="module")
def smtp_test_module(request, _smtp_test_session):
    _smtp_test_session.set_test_name(request.node.name)
    _smtp_test_session.clear_database()
    yield _smtp_test_session
    _smtp_test_session.clear_database()


@pytest.yield_fixture(scope="function")
def smtp_test(request, smtp_test_module):
    smtp_test_module.set_test_name(request.node.name)
    smtp_test_module.clear_database()
    yield smtp_test_module
    smtp_test_module.clear_database()
