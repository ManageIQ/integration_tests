import random
import re
from threading import Timer
from urllib.parse import urlparse

import attr
import pytest
from cached_property import cached_property

from cfme.test_framework.sprout.client import AuthException
from cfme.test_framework.sprout.client import SproutClient
from cfme.test_framework.sprout.client import SproutException
from cfme.utils import at_exit
from cfme.utils import conf
from cfme.utils.config_data import cfme_data
from cfme.utils.log import logger as log
from cfme.utils.path import project_path
from cfme.utils.wait import wait_for
# todo: use own logger after logfix merge


_appliance_help = '''specify appliance URLs to use for distributed testing.
this option can be specified more than once, and must be specified at least two times'''


def pytest_addoption(parser):
    group = parser.getgroup("cfme")
    group.addoption(
        '--appliance',
        dest='appliances',
        action='append',
        metavar='appliance_url',
        help=_appliance_help,
        default=[]
    )
    group.addoption(
        '--use-sprout',
        dest='use_sprout',
        action='store_true',
        default=False,
        help="Use Sprout for provisioning appliances."
    )
    group.addoption(
        '--sprout-appliances',
        dest='sprout_appliances',
        type=int,
        default=1,
        help="How many Sprout appliances to use?."
    )
    group.addoption(
        '--sprout-timeout',
        dest='sprout_timeout',
        type=int,
        default=60,
        help="How many minutes is the lease timeout."
    )
    group.addoption(
        '--sprout-provision-timeout',
        dest='sprout_provision_timeout',
        type=int,
        default=60,
        help="How many minutes to wait for appliances provisioned."
    )
    group.addoption(
        '--sprout-group',
        dest='sprout_group',
        default=None,
        help="Which stream to use."
    )
    group.addoption(
        '--sprout-version',
        dest='sprout_version',
        default=None,
        help="Which version to use."
    )
    group.addoption(
        '--sprout-date',
        dest='sprout_date',
        default=None,
        help="Which date to use."
    )
    group.addoption(
        '--sprout-desc',
        dest='sprout_desc',
        default=None,
        help="Set description of the pool."
    )
    group.addoption(
        '--sprout-override-ram',
        dest='sprout_override_ram',
        type=int,
        default=0,
        help="Override RAM (MB). 0 means no override."
    )
    group.addoption(
        '--sprout-override-cpu',
        dest='sprout_override_cpu',
        type=int,
        default=0,
        help="Override CPU core count. 0 means no override."
    )
    group.addoption(
        '--sprout-provider',
        dest='sprout_provider',
        default=None,
        help="Which provider to use."
    )
    group.addoption(
        '--sprout-provider-type',
        dest='sprout_provider_type',
        default=None,
        help="Sprout provider type - openshift, etc"
    )
    group.addoption(
        '--sprout-template-type',
        dest='sprout_template_type',
        default=None,
        help="Specifies which template type to use openshift_pod, virtual_machine, docker_vm"
    )
    group.addoption(
        '--sprout-ignore-preconfigured',
        dest='sprout_template_preconfigured',
        default=True,
        action="store_false",
        help="Allows to use not preconfigured templates"
    )
    group.addoption(
        '--sprout-user-key',
        default=None,
        help='Key for sprout user in credentials yaml, '
             'alternatively set SPROUT_USER and SPROUT_PASSWORD env vars'
    )


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


def mangle_in_sprout_appliances(config):
    """
    this helper function resets the appliances option of the config and mangles in
    the sprout ones

    its a hopefully temporary hack until we make a correctly ordered hook for obtaining appliances
    """
    provision_request = SproutProvisioningRequest.from_config(config)

    mgr = config._sprout_mgr = SproutManager(config.option.sprout_user_key)
    try:
        requested_appliances = mgr.request_appliances(provision_request)
    except AuthException:
        log.exception('Sprout client not authenticated, please provide env vars or sprout_user_key')
        raise
    config.option.appliances[:] = []
    appliances = config.option.appliances
    log.info("Appliances were provided:")
    for appliance in requested_appliances:

        appliance_args = {'hostname': appliance['url']}
        provider_data = cfme_data['management_systems'].get(appliance['provider'])
        if provider_data and provider_data['type'] == 'openshift':
            ocp_creds = conf.credentials[provider_data['credentials']]
            ssh_creds = conf.credentials[provider_data['ssh_creds']]
            extra_args = {
                'container': appliance['container'],
                'db_host': appliance['db_host'],
                'project': appliance['project'],
                'openshift_creds': {
                    'hostname': provider_data['hostname'],
                    'username': ocp_creds['username'],
                    'password': ocp_creds['password'],
                    'ssh': {
                        'username': ssh_creds['username'],
                        'password': ssh_creds['password'],
                    }
                }
            }
            appliance_args.update(extra_args)
        appliances.append(appliance_args)
        log.info("- %s is %s", appliance['url'], appliance['name'])
    mgr.reset_timer()
    template_name = requested_appliances[0]["template_name"]
    conf.runtime["cfme_data"]["basic_info"]["appliance_template"] = template_name
    log.info("appliance_template: %s", template_name)
    with project_path.join('.appliance_template').open('w') as template_file:
        template_file.write('export appliance_template="{}"'.format(template_name))
    log.info("Sprout setup finished.")

    config.pluginmanager.register(ShutdownPlugin())


@attr.s
class SproutProvisioningRequest(object):
    """data holder for provisioning metadata"""

    group = attr.ib()
    count = attr.ib(default=1)
    version = attr.ib(default=None)
    provider = attr.ib(default=None)
    provider_type = attr.ib(default=None)
    template_type = attr.ib(default=None)
    preconfigured = attr.ib(default=True)
    date = attr.ib(default=None)
    lease_time = attr.ib(default=60)
    desc = attr.ib(default=None)
    provision_timeout = attr.ib(default=60)

    cpu = attr.ib(default=0)
    ram = attr.ib(default=0)

    @classmethod
    def from_config(cls, config):
        return cls(
            group=config.option.sprout_group,
            count=config.option.sprout_appliances,
            version=config.option.sprout_version,
            provider=config.option.sprout_provider,
            provider_type=config.option.sprout_provider_type,
            template_type=config.option.sprout_template_type,
            preconfigured=config.option.sprout_template_preconfigured,
            date=config.option.sprout_date,
            lease_time=config.option.sprout_timeout,
            desc=config.option.sprout_desc,
            provision_timeout=config.option.sprout_provision_timeout,
            cpu=config.option.sprout_override_cpu or None,
            ram=config.option.sprout_override_ram or None,
        )


@attr.s
class SproutManager(object):
    sprout_user_key = attr.ib(default=None)
    pool = attr.ib(init=False, default=None)
    lease_time = attr.ib(init=False, default=None, repr=False)
    timer = attr.ib(init=False, default=None, repr=False)

    @cached_property
    def client(self):
        """Provide additional kwargs to from_config for auth passing"""
        return SproutClient.from_config(sprout_user_key=self.sprout_user_key)

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

        kargs = {
            'count': provision_request.count,
            'version': provision_request.version,
            'provider': provision_request.provider,
            'provider_type': provision_request.provider_type,
            'preconfigured': provision_request.preconfigured,
            'date': provision_request.date,
            'lease_time': provision_request.lease_time,
            'cpu': provision_request.cpu,
            'ram': provision_request.ram,
            'stream': provision_request.group,
            'wait_time': provision_request.provision_timeout * 60
        }
        if provision_request.template_type:
            kargs['template_type'] = provision_request.template_type

        apps, pool_id = self.client.provision_appliances(**kargs)
        self.pool = pool_id
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
        return result["finished"]

    def clean_jenkins_job(self, jenkins_job):
        try:
            log.info(
                "Check if pool already exists for this %r Jenkins job", jenkins_job[0])
            jenkins_job_pools = self.client.find_pools_by_description(jenkins_job[0], partial=True)
            for pool in jenkins_job_pools:
                # Some jobs have overlapping descriptions, sprout API doesn't support regex
                # job-name-12345 vs job-name-master-12345
                # the partial match alone will catch both of these, use regex to confirm pool
                # description is an accurate match
                if self.client.get_pool_description(pool) == '{}{}'.format(jenkins_job[0], pool):
                    log.info("Destroying the old pool %s for %r job.", pool, jenkins_job[0])
                    self.client.destroy_pool(pool)
                else:
                    log.info('Skipped pool destroy due to potential pool description overlap: %r',
                             jenkins_job[0])
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
            self.client.prolong_appliance_pool_lease(self.pool, self.lease_time)
        except SproutException as e:
            log.exception(
                "Pool %s does not exist any more, disabling the timer.\n"
                "This can happen before the tests are shut down "
                "(last deleted appliance deleted the pool\n"
                "> The exception was: %s", self.pool, str(e))
            self.pool = None  # Will disable the timer in next reset call.
        except Exception as e:
            log.error('An unexpected error happened during interaction with Sprout:')
            log.exception(e)
            # Have a shorter timer now (1 min), because something is happening right now
            # WE have a reserve of half the lease time so that should be enough time to
            # solve any minor problems
            # Adding a 0-10 extra random sec just for sake of dispersing any possible "swarm"
            timeout = 60 + random.randint(0, 10)
        finally:
            self.reset_timer(timeout=timeout)


def pytest_addhooks(pluginmanager):
    pluginmanager.add_hookspecs(NewHooks)


class ShutdownPlugin(object):

    def pytest_miq_node_shutdown(self, config, nodeinfo):
        if config.getoption('ui_coverage'):
            # TODO: Ensure this gets called after pytest_sessionfinish
            # This disables the appliance deletion when ui coverage is on. ^
            # This is because we need one of the appliances to do the collection for us
            return
        if nodeinfo:
            netloc = urlparse(nodeinfo).netloc
            ip_address = netloc.split(":")[0]
            log.debug("Trying to end appliance {}".format(ip_address))
            if config.getoption('--use-sprout'):
                try:
                    call_method = config._sprout_mgr.client.call_method
                    log.debug("appliance data %r", call_method('appliance_data', ip_address))
                    log.debug(
                        "destroy appliance result: %r",
                        call_method('destroy_appliance', ip_address))
                except Exception as e:
                    log.debug('Error trying to end sprout appliance %s', ip_address)
                    log.debug(e)
            else:
                log.debug('Not a sprout run so not doing anything for %s', ip_address)
        else:
            log.debug('The IP address was not present - not terminating any appliance')


class NewHooks(object):
    def pytest_miq_node_shutdown(self, config, nodeinfo):
        pass
