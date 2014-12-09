# -*- coding: utf-8 -*-
"""Module designed to handle the simple case when one wants to use Sprout but does not use the
parallelizer. Uses IPAppliance that is pushed on top of the appliance stack"""
import pytest

from threading import Timer

from fixtures.terminalreporter import reporter
from utils import at_exit
from utils.appliance import IPAppliance
from utils.sprout import SproutClient
from utils.wait import wait_for


timer = None
appliance = None


def ping_pool(sprout, pool, timeout):
    sprout.prolong_appliance_pool_lease(pool)
    reset_timer(sprout, pool, timeout)


def reset_timer(sprout, pool, timeout):
    global timer
    if timer:
        timer.cancel()
    timer = Timer((timeout / 2) * 60, lambda: ping_pool(sprout, pool, timeout))
    timer.daemon = True
    timer.start()


def pytest_configure(config, __multicall__):
    global appliance
    __multicall__.execute()
    if not config.option.appliances and (config.option.use_sprout
            and config.option.sprout_appliances == 1):
        terminal = reporter()
        sprout = SproutClient.from_config()
        terminal.write("Requesting single appliance from sprout...\n")
        pool_id = sprout.request_appliances(
            config.option.sprout_group,
            provider=config.option.sprout_provider,
            template=config.option.sprout_template,
            count=config.option.sprout_appliances,
            version=config.option.sprout_version,
            date=config.option.sprout_date,
            lease_time=config.option.sprout_timeout
        )
        terminal.write("Appliance pool {}. Waiting for fulfillment ...\n".format(pool_id))
        at_exit(sprout.destroy_pool, pool_id)
        wait_for(
            lambda: sprout.request_check(pool_id)["fulfilled"],
            num_sec=30 * 60,  # 30 minutes
            delay=5,
            message="requesting appliance was fulfilled"
        )
        request = sprout.request_check(pool_id)
        ip_address = request["appliances"][0]["ip_address"]
        terminal.write("Appliance requested at address {} ...\n".format(ip_address))
        reset_timer(sprout, pool_id, config.option.sprout_timeout)
        terminal.write("Appliance lease timer is running ...\n")
        appliance = IPAppliance(address=ip_address)


@pytest.mark.tryfirst
def pytest_sessionstart(session):
    global appliance
    if appliance is not None:
        appliance.push()


@pytest.mark.trylast
def pytest_sessionfinish(session, exitstatus):
    global appliance
    if appliance is not None:
        appliance.pop()
        appliance = None
