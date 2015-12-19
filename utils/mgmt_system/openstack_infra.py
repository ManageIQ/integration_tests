# coding: utf-8
from keystoneclient.v2_0 import client as oskclient
from novaclient import client as osclient
from novaclient.client import HTTPClient
from requests.exceptions import Timeout

from utils.log import logger
from mgmtsystem.base import MgmtSystemAPIBase


# TODO The following monkeypatch nonsense is criminal, and would be
# greatly simplified if openstack made it easier to specify a custom
# client class. This is a trivial PR that they're likely to accept.

# Note: This same mechanism may be required for keystone and cinder
# clients, but hopefully won't be.

# monkeypatch method to add retry support to openstack
def _request_timeout_handler(self, url, method, retry_count=0, **kwargs):
    try:
        # Use the original request method to do the actual work
        return HTTPClient.request(self, url, method, **kwargs)
    except Timeout:
        if retry_count >= 3:
            logger.error('nova request timed out after {} retries'.format(retry_count))
            raise
        else:
            # feed back into the replaced method that supports retry_count
            retry_count += 1
            logger.info('nova request timed out; retry {}'.format(retry_count))
            return self.request(url, method, retry_count=retry_count, **kwargs)


class OpenstackInfraSystem(MgmtSystemAPIBase):
    """Openstack Infrastructure management system

    # TODO
    """

    _stats_available = {
        'num_template': lambda self: len(self.list_template()),
        'num_host': lambda self: len(self.list_host()),
    }

    states = {
        'running': ('ACTIVE',),
        'stopped': ('SHUTOFF',),
        'suspended': ('SUSPENDED',),
    }

    can_suspend = True

    def __init__(self, **kwargs):
        self.tenant = kwargs['tenant']
        self.username = kwargs['username']
        self.password = kwargs['password']
        self.auth_url = kwargs['auth_url']
        self._api = None
        self._kapi = None
        self._capi = None

    @property
    def api(self):
        if not self._api:
            self._api = osclient.Client('2',
                                        self.username,
                                        self.password,
                                        self.tenant,
                                        self.auth_url,
                                        service_type="compute",
                                        insecure=True,
                                        timeout=30)
            # replace the client request method with our version that
            # can handle timeouts; uses explicit binding (versus
            # replacing the method directly on the HTTPClient class)
            # so we can still call out to HTTPClient's original request
            # method in the timeout handler method
            self._api.client.request = _request_timeout_handler.__get__(self._api.client,
                HTTPClient)
        return self._api

    @property
    def kapi(self):
        if not self._kapi:
            self._kapi = oskclient.Client(username=self.username,
                                          password=self.password,
                                          tenant_name=self.tenant,
                                          auth_url=self.auth_url,
                                          insecure=True)
        return self._kapi

    @property
    def nodes(self):
        return self.api.servers.list()

    @property
    def images(self):
        return self.api.images.list()

    @property
    def networks(self):
        return self.api.networks.list()

    def start_vm(self, vm_name):
        raise NotImplementedError('start_vm not implemented.')

    def wait_vm_running(self, vm_name, num_sec):
        raise NotImplementedError('wait_vm_running not implemented.')

    def stop_vm(self, vm_name):
        raise NotImplementedError('stop_vm not implemented.')

    def wait_vm_stopped(self, vm_name, num_sec):
        raise NotImplementedError('wait_vm_stopped not implemented.')

    def create_vm(self, vm_name):
        raise NotImplementedError('create_vm not implemented.')

    def delete_vm(self, vm_name):
        raise NotImplementedError('delete_vm not implemented.')

    def restart_vm(self, vm_name):
        raise NotImplementedError('restart_vm not implemented.')

    def vm_status(self, vm_name):
        raise NotImplementedError('vm_status not implemented.')

    def is_vm_running(self, vm_name):
        raise NotImplementedError('is_vm_running not implemented.')

    def is_vm_stopped(self, vm_name):
        raise NotImplementedError('is_vm_stopped not implemented.')

    def is_vm_suspended(self, vm_name):
        raise NotImplementedError('is_vm_suspended not implemented.')

    def suspend_vm(self, vm_name):
        raise NotImplementedError('restart_vm not implemented.')

    def wait_vm_suspended(self, vm_name, num_sec):
        raise NotImplementedError('wait_vm_suspended not implemented.')

    def list_vm(self, **kwargs):
        raise NotImplementedError('list_vm not implemented.')

    def list_template(self):
        return [image.name for image in self.images]

    def list_flavor(self):
        raise NotImplementedError('list_flavor not implemented.')

    def list_network(self):
        return [network.name for network in self.networks]

    def list_host(self):
        return [node.name for node in self.nodes]

    def info(self):
        raise NotImplementedError('info not implemented.')

    def disconnect(self):
        pass

    def clone_vm(self, source_name, vm_name):
        raise NotImplementedError()

    def does_vm_exist(self, name):
        raise NotImplementedError()

    def deploy_template(self, template, *args, **kwargs):
        raise NotImplementedError()

    def current_ip_address(self, vm_name):
        raise NotImplementedError()

    def get_ip_address(self, vm_name):
        ""
        raise NotImplementedError()

    def remove_host_from_cluster(self, hostname):
        raise NotImplementedError()

    # TODO
