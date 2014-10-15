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
from fixtures.artifactor_plugin import art_client
from utils.conf import env
from utils.log import create_logger
from utils.net import random_port, my_ip_address, net_check_remote
from utils.path import scripts_path
from utils.smtp_collector_client import SMTPCollectorClient


logger = create_logger('emails')


@pytest.fixture(scope="session")
def _smtp_test_session(request):
    """Fixture, which prepares the appliance for e-mail capturing tests

    Returns: :py:class:`util.smtp_collector_client.SMTPCollectorClient` instance.
    """
    logger.info("Preparing start for e-mail collector")
    ports = env.get("mail_collector", {}).get("ports", {})
    mail_server_port = ports.get("smtp", None) or random_port()
    mail_query_port = ports.get("json", None) or random_port()
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
    collector = None

    def _finalize():
        if collector is None:
            return
        logger.info("Sending KeyboardInterrupt to collector")
        collector.send_signal(signal.SIGINT)
        time.sleep(2)
        if collector.poll() is None:
            logger.info("Sending SIGTERM to collector")
            collector.send_signal(signal.SIGTERM)
            time.sleep(5)
            if collector.poll() is None:
                logger.info("Sending SIGKILL to collector")
                collector.send_signal(signal.SIGKILL)
        collector.wait()
        logger.info("Collector finished")
    collector = subprocess.Popen(server_command, shell=True)
    request.addfinalizer(_finalize)
    logger.info("Collector pid %d" % collector.pid)
    logger.info("Waiting for collector to become alive.")
    time.sleep(3)
    assert collector.poll() is None, "Collector has died. Something must be blocking selected ports"
    logger.info("Collector alive")
    query_port_open = net_check_remote(mail_query_port, my_ip, force=True)
    server_port_open = net_check_remote(mail_server_port, my_ip, force=True)
    assert query_port_open and server_port_open,\
        'Ports %d and %d on the machine executing the tests are closed.\n'\
        'The ports are randomly chosen -> turn firewall off.'\
        % (mail_query_port, mail_server_port)
    client = SMTPCollectorClient(
        my_ip,
        mail_query_port
    )
    return client


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


@pytest.mark.trylast
def pytest_runtest_call(__multicall__, item):
    __multicall__.execute()
    if "smtp_test" not in item.funcargs:
        return

    art_client.fire_hook(
        "filedump",
        test_name=item.name,
        test_location=item.parent.name,
        filename="emails.html",
        contents=item.funcargs["smtp_test"].get_html_report(),
        fd_ident="emails"
    )
