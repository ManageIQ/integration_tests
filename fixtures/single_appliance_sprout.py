# -*- coding: utf-8 -*-
"""Module designed to handle the simple case when one wants to use Sprout but does not use the
parallelizer. Uses IPAppliance that is pushed on top of the appliance stack"""
import pytest

from threading import Timer

from fixtures.parallelizer import dump_pool_info
from fixtures.terminalreporter import reporter
from utils import at_exit, conf
from utils.appliance import IPAppliance, stack as appliance_stack
from utils.path import project_path
from utils.sprout import SproutClient
from utils.wait import wait_for

# todo introduce a sproutstate plugin

timer = None
appliance = None
pool_id = None
sprout = None


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


@pytest.mark.tryfirst
@pytest.mark.hookwrapper
def pytest_configure(config):
    global appliance
    global pool_id
    global sprout
    if not config.option.appliances and (config.option.use_sprout and
            config.option.sprout_appliances == 1):
        terminal = reporter()
        sprout = SproutClient.from_config()
        terminal.write("Requesting a single appliance from sprout...\n")
        pool_id = sprout.request_appliances(
            config.option.sprout_group,
            count=config.option.sprout_appliances,
            version=config.option.sprout_version,
            date=config.option.sprout_date,
            lease_time=config.option.sprout_timeout
        )
        terminal.write("Appliance pool {}. Waiting for fulfillment ...\n".format(pool_id))
        at_exit(destroy_the_pool)
        if config.option.sprout_desc is not None:
            sprout.set_pool_description(pool_id, str(config.option.sprout_desc))
        try:
            result = wait_for(
                lambda: sprout.request_check(pool_id)["fulfilled"],
                num_sec=config.option.sprout_provision_timeout * 60,
                delay=5,
                message="requesting appliance was fulfilled"
            )
        except:
            pool = sprout.request_check(pool_id)
            dump_pool_info(lambda x: terminal.write("{}\n".format(x)), pool)
            terminal.write("Destroying the pool on error.\n")
            sprout.destroy_pool(pool_id)
            raise
        terminal.write("Provisioning took {0:.1f} seconds\n".format(result.duration))
        request = sprout.request_check(pool_id)
        ip_address = request["appliances"][0]["ip_address"]
        terminal.write("Appliance requested at address {} ...\n".format(ip_address))
        reset_timer(sprout, pool_id, config.option.sprout_timeout)
        terminal.write("Appliance lease timer is running ...\n")
        appliance = IPAppliance(address=ip_address)
        appliance_stack.push(appliance)
        # Retrieve and print the template_name for Jenkins to pick up
        template_name = request["appliances"][0]["template_name"]
        conf.runtime["cfme_data"]["basic_info"]["appliance_template"] = template_name
        terminal.write("appliance_template=\"{}\";\n".format(template_name))
        with project_path.join('.appliance_template').open('w') as template_file:
            template_file.write('export appliance_template="{}"'.format(template_name))
        terminal.write("Single appliance Sprout setup finished.\n")
        # And set also the appliances_provider
        provider = request["appliances"][0]["provider"]
        terminal.write("appliance_provider=\"{}\";\n".format(provider))
        conf.runtime["cfme_data"]["basic_info"]["appliances_provider"] = provider
    yield


@pytest.mark.hookwrapper
def pytest_sessionfinish(session, exitstatus):
    global appliance
    global timer
    global pool_id
    global sprout
    yield
    terminal = reporter()
    if timer is not None:
        terminal.write("Stopping timer\n")
        timer.cancel()
        timer = None
    if appliance is not None:
        terminal.write("Popping out the appliance\n")
        appliance_stack.pop()
        appliance = None
    destroy_the_pool()


def destroy_the_pool():
    global sprout
    global pool_id
    terminal = reporter()
    if sprout is not None and pool_id is not None and sprout.pool_exists(pool_id):
        terminal.write("Destroying pool {}\n".format(pool_id))
        try:
            sprout.destroy_pool(pool_id)
            wait_for(lambda: not sprout.pool_exists(pool_id), num_sec=300, delay=10)
        except Exception as e:
            terminal.write("Exception raised: {} - {}\n".format(type(e).__name__, str(e)))
        sprout = None
        pool_id = None
