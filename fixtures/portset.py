# -*- coding: utf-8 -*-
from utils import ports
from utils.log import logger


def pytest_addoption(parser):
    group = parser.getgroup('Port override')
    group.addoption('--port-db',
                    action='store',
                    default=None,
                    dest='port_db',
                    help="Override appliance's database port.")
    group.addoption('--port-ssh',
                    action='store',
                    default=None,
                    dest='port_ssh',
                    help="Override appliance's SSH port.")


def pytest_configure(config):
    # SSH
    port_ssh = config.getoption("port_ssh")
    if port_ssh is not None:
        logger.info("Overriding SSH port to {}.".format(str(port_ssh)))
        ports.SSH = int(port_ssh)
    # DB
    port_db = config.getoption("port_db")
    if port_db is not None:
        logger.info("Overriding DB port to {}.".format(str(port_db)))
        ports.DB = int(port_db)
