# -*- coding: utf-8 -*-
"""This module provides a fixture useful for checking the e-mails arrived.

Main use is of fixture :py:meth:`smtp_test`, which is function scoped. There is also
a :py:meth:`smtp_test_module` fixture for which the smtp_test is just a function-scoped wrapper
to speed things up. The base of all this is the session-scoped _smtp_test_session that keeps care
about the collector.
"""
import logging
import os
import pytest
import signal
import subprocess
import time

from cfme.configure import configuration
from fixtures.artifactor_plugin import fire_art_test_hook
from cfme.utils.conf import env
from cfme.utils.log import setup_logger
from cfme.utils.net import random_port, my_ip_address, net_check_remote
from cfme.utils.path import scripts_path
from cfme.utils.smtp_collector_client import SMTPCollectorClient


logger = setup_logger(logging.getLogger('emails'))


@pytest.fixture(scope="function")
def smtp_test(request):
    """Fixture, which prepares the appliance for e-mail capturing tests

    Returns: :py:class:`util.smtp_collector_client.SMTPCollectorClient` instance.
    """
    logger.info("Preparing start for e-mail collector")
    ports = env.get("mail_collector", {}).get("ports", {})
    mail_server_port = ports.get("smtp", False) or os.getenv('SMTP', False) or random_port()
    mail_query_port = ports.get("json", False) or os.getenv('JSON', False) or random_port()
    my_ip = my_ip_address()
    logger.info("Mind that it needs ports %s and %s open", mail_query_port, mail_server_port)
    smtp_conf = configuration.SMTPSettings(
        host=my_ip,
        port=mail_server_port,
        auth="none",
    )
    smtp_conf.update()
    server_filename = scripts_path.join('smtp_collector.py').strpath
    server_command = server_filename + " --smtp-port {} --query-port {}".format(
        mail_server_port,
        mail_query_port
    )
    logger.info("Starting mail collector %s", server_command)
    collector = None

    def _finalize():
        if collector is None:
            return
        logger.info("Sending KeyboardInterrupt to collector")
        try:
            collector.send_signal(signal.SIGINT)
        except OSError as e:
            # TODO: Better logging.
            logger.exception(e)
            logger.error("Something happened to the e-mail collector!")
            return
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
        logger.info("Cleaning up smtp setup in CFME")
        smtp_conf = configuration.SMTPSettings(
            host='',
            port='',
        )
        smtp_conf.update()
    collector = subprocess.Popen(server_command, shell=True)
    request.addfinalizer(_finalize)
    logger.info("Collector pid %s", collector.pid)
    logger.info("Waiting for collector to become alive.")
    time.sleep(3)
    assert collector.poll() is None, "Collector has died. Something must be blocking selected ports"
    logger.info("Collector alive")
    query_port_open = net_check_remote(mail_query_port, my_ip, force=True)
    server_port_open = net_check_remote(mail_server_port, my_ip, force=True)
    assert query_port_open and server_port_open,\
        'Ports {} and {} on the machine executing the tests are closed.\n'\
        'The ports are randomly chosen -> turn firewall off.'\
        .format(mail_query_port, mail_server_port)
    client = SMTPCollectorClient(
        my_ip,
        mail_query_port
    )
    client.set_test_name(request.node.name)
    client.clear_database()
    return client


@pytest.mark.hookwrapper
def pytest_runtest_call(item):
    try:
        yield
    finally:
        if "smtp_test" not in item.funcargs:
            return

        try:
            fire_art_test_hook(
                item,
                "filedump",
                description="received e-mails",
                contents=item.funcargs["smtp_test"].get_html_report(),
                file_type="html",
                display_glyph="align-justify",
                group_id="misc-artifacts",
            )
        except Exception as e:
            logger.exception(e)
            logger.error("Something happened to the SMTP collector.")
