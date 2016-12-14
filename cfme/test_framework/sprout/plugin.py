import re
import pytest
import random
import attr
from threading import Timer
from utils import at_exit, conf
from utils.appliance import IPAppliance, stack as appliance_stack
# todo: use own logger after logfix merge
from utils.log import logger as log
from utils.path import project_path
from .client import SproutClient, SproutException
from utils.wait import wait_for


_appliance_help = '''specify appliance URLs to use for distributed testing.
this option can be specified more than once, and must be specified at least two times'''

# Todo: hack taken from parallelizer, restructure
env_base_urls = conf.env.get('parallel_base_urls', [])
if env_base_urls:
    conf.runtime['env']['base_url'] = env_base_urls[0]


def pytest_addoption(parser):
    group = parser.getgroup("cfme")
    group._addoption('--appliance', dest='appliances', action='append',
        default=env_base_urls, metavar='base_url', help=_appliance_help)
    group._addoption('--use-sprout', dest='use_sprout', action='store_true',
        default=False, help="Use Sprout for provisioning appliances.")
    group._addoption('--sprout-appliances', dest='sprout_appliances', type=int,
        default=1, help="How many Sprout appliances to use?.")
    group._addoption('--sprout-timeout', dest='sprout_timeout', type=int,
        default=60, help="How many minutes is the lease timeout.")
    group._addoption('--sprout-provision-timeout', dest='sprout_provision_timeout', type=int,
        default=60, help="How many minutes to wait for appliances provisioned.")
    group._addoption(
        '--sprout-group', dest='sprout_group', default=None, help="Which stream to use.")
    group._addoption(
        '--sprout-version', dest='sprout_version', default=None, help="Which version to use.")
    group._addoption(
        '--sprout-date', dest='sprout_date', default=None, help="Which date to use.")
    group._addoption(
        '--sprout-desc', dest='sprout_desc', default=None, help="Set description of the pool.")


def dump_pool_info(log, pool_data):
    log.info("Fulfilled: %s", pool_data["fulfilled"])
    log.info("Progress: %s%%", pool_data["progress"])
    log.info("Appliances:")
    for appliance in pool_data["appliances"]:
        name = appliance["name"]
        log.info("\t%s:", name)
        for key in sorted(appliance.keys()):
            if key == "name":
                continue
            log.info("\t\t%s: %s", key, appliance[key])


@pytest.mark.tryfirst
def pytest_configure(config):
    if config.getoption("appliances"):
        return
    if not config.getoption('--use-sprout'):
        return

    provision_request = SproutProvisioningRequest.from_config(config)

    mgr = config._sprout_mgr = SproutManager()
    requested_appliances = mgr.request_appliances(provision_request)
    config.option.appliances[:] = []
    appliances = config.option.appliances
    # Push an appliance to the stack to have proper reference for test collection
    # FIXME: this is a bad hack based on the need for controll of collection partitioning
    appliance_stack.push(
        IPAppliance(address=requested_appliances[0]["ip_address"]))
    log.info("Appliances were provided:")
    for appliance in requested_appliances:
        url = "https://{}/".format(appliance["ip_address"])
        appliances.append(url)
        log.info("- %s is %s", url, appliance['name'])

    mgr.reset_timer()
    # Set the base_url for collection purposes on the first appliance
    conf.runtime["env"]["base_url"] = appliances[0]
    # Retrieve and print the template_name for Jenkins to pick up
    template_name = requested_appliances[0]["template_name"]
    conf.runtime["cfme_data"]["basic_info"]["appliance_template"] = template_name
    log.info("appliance_template: %s", template_name)
    with project_path.join('.appliance_template').open('w') as template_file:
        template_file.write('export appliance_template="{}"'.format(template_name))
    log.info("Sprout setup finished.")


@attr.s
class SproutProvisioningRequest(object):
    """data holder for provisioning metadata"""

    group = attr.ib()
    count = attr.ib()
    version = attr.ib()
    date = attr.ib()
    lease_time = attr.ib()
    desc = attr.ib()
    provision_timeout = attr.ib()

    @classmethod
    def from_config(cls, config):
        return cls(
            group=config.option.sprout_group,
            count=config.option.sprout_appliances,
            version=config.option.sprout_version,
            date=config.option.sprout_date,
            lease_time=config.option.sprout_timeout,
            desc=config.option.sprout_desc,
            provision_timeout=config.option.sprout_provision_timeout,
        )


@attr.s
class SproutManager(object):
    client = attr.ib(default=attr.Factory(SproutClient.from_config))
    pool = attr.ib(init=False, default=None)
    lease_time = attr.ib(init=False, default=None, repr=False)
    timer = attr.ib(init=False, default=None, repr=False)

    def request_appliances(self, provision_request):
        self.request_pool(provision_request)

        try:
            result = wait_for(
                self.check_fullfilled,
                num_sec=provision_request.provision_timeout * 60,
                delay=5,
                message="requesting appliances was fulfilled"
            )
        except Exception:
            pool = self.request_check()
            dump_pool_info(log, pool)
            log.debug("Destroying the pool on error.")
            self.destroy_pool()
            raise
        else:
            at_exit(self.destroy_pool)
            pool = self.request_check()
            dump_pool_info(log, pool)

        log.info("Provisioning took %.1f seconds", result.duration)
        return pool["appliances"]

    def request_pool(self, provision_request):
        log.info("Requesting %s appliances from Sprout at %s",
                 provision_request.count, self.client.api_entry)
        self.lease_time = provision_request.lease_time
        if provision_request.desc is not None:
            jenkins_job = re.findall(r"Jenkins.*[^\d+$]", provision_request.desc)
            if jenkins_job:
                self.clean_jenkins_job(jenkins_job)

        self.pool = self.client.request_appliances(
            provision_request.group,
            count=provision_request.count,
            version=provision_request.version,
            date=provision_request.date,
            lease_time=provision_request.lease_time,
        )
        log.info("Pool %s. Waiting for fulfillment ...", self.pool)

        if provision_request.desc is not None:
            self.client.set_pool_description(self.pool, provision_request.desc)

    def destroy_pool(self):
        try:
            self.client.destroy_pool(self.pool)
        except Exception:
            pass

    def request_check(self):
        return self.client.request_check(self.pool)

    def check_fullfilled(self):
        try:
            result = self.request_check()
        except SproutException as e:
            # TODO: ensure we only exit this way on sprout usage
            self.destroy_pool()
            log.error("sprout pool could not be fulfilled\n%s", str(e))
            pytest.exit(1)

        log.debug("fulfilled at %f %%", result['progress'])
        return result["fulfilled"]

    def clean_jenkins_job(self, jenkins_job):
        try:
            log.info(
                "Check if pool already exists for this %r Jenkins job", jenkins_job[0])
            jenkins_job_pools = self.client.find_pools_by_description(jenkins_job[0], partial=True)
            for pool in jenkins_job_pools:
                log.info("Destroying the old pool %s for %r job.", pool, jenkins_job[0])
                self.client.destroy_pool(pool)
        except Exception:
            log.exception(
                "Exception occurred during old pool deletion, this can be ignored"
                "proceeding to Request new pool")

    def reset_timer(self, timeout=None):
        if self.pool is None:
            if self.timer:
                self.timer.cancel()  # Cancel it anyway
                log.info("Sprout timer cancelled")
            return
        if self.timer:
            self.timer.cancel()
        timeout = timeout or ((self.lease_time / 2) * 60)
        self.timer = Timer(timeout, self.ping_pool)
        self.timer.daemon = True
        self.timer.start()

    def ping_pool(self):
        timeout = None  # None - keep the half of the lease time
        try:
            self.client.prolong_appliance_pool_lease(self.pool)
        except SproutException as e:
            log.exception(
                "Pool %s does not exist any more, disabling the timer.\n"
                "This can happen before the tests are shut down "
                "(last deleted appliance deleted the pool\n"
                "> The exception was: %s", self.pool, str(e))
            self.pool = None  # Will disable the timer in next reset call.
        except Exception as e:
            self.log.error('An unexpected error happened during interaction with Sprout:')
            self.log.exception(e)
            # Have a shorter timer now (1 min), because something is happening right now
            # WE have a reserve of half the lease time so that should be enough time to
            # solve any minor problems
            # Adding a 0-10 extra random sec just for sake of dispersing any possible "swarm"
            timeout = 60 + random.randint(0, 10)
        finally:
            self.reset_timer(timeout=timeout)
