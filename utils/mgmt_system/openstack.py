# coding: utf-8
"""Backend management system classes

Used to communicate with providers without using CFME facilities
"""
from contextlib import contextmanager
from datetime import datetime

from cinderclient.v2 import client as cinderclient
from cinderclient import exceptions as cinder_exceptions
from keystoneclient.v2_0 import client as oskclient
from novaclient.v1_1 import client as osclient
from novaclient import exceptions as os_exceptions
from novaclient.client import HTTPClient
from requests.exceptions import Timeout

from cfme import exceptions as cfme_exc
from utils.log import logger
from utils.mgmt_system.base import MgmtSystemAPIBase, VMInfo
from utils.mgmt_system.exceptions import (
    NetworkNameNotFound, VMInstanceNotFound
)
from utils.timeutil import local_tz
from utils.version import current_version
from utils.wait import wait_for


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


class OpenstackSystem(MgmtSystemAPIBase):
    """Openstack management system

    Uses novaclient.

    Args:
        tenant: The tenant to log in with.
        username: The username to connect with.
        password: The password to connect with.
        auth_url: The authentication url.

    """

    _stats_available = {
        'num_vm': lambda self: self._num_vm_stat(),
        'num_template': lambda self: len(self.list_template()),
    }

    states = {
        'paused': ('PAUSED',),
        'running': ('ACTIVE',),
        'stopped': ('SHUTOFF',),
        'suspended': ('SUSPENDED',),
    }

    can_suspend = True
    can_pause = True

    def __init__(self, **kwargs):
        self.tenant = kwargs['tenant']
        self.username = kwargs['username']
        self.password = kwargs['password']
        self.auth_url = kwargs['auth_url']
        self._api = None
        self._kapi = None
        self._capi = None

    def _num_vm_stat(self):
        if current_version() < '5.3':
            filter_tenants = False
        else:
            filter_tenants = True
        return len(self._get_all_instances(filter_tenants))

    @property
    def api(self):
        if not self._api:
            self._api = osclient.Client(self.username,
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
    def capi(self):
        if not self._capi:
            self._capi = cinderclient.Client(self.username,
                                             self.password,
                                             self.tenant,
                                             self.auth_url,
                                             service_type="volume",
                                             insecure=True)
        return self._capi

    def _get_tenants(self):
        real_tenants = []
        tenants = self.kapi.tenants.list()
        for tenant in tenants:
            users = tenant.list_users()
            user_list = [user.name for user in users]
            if self.username in user_list:
                real_tenants.append(tenant)
        return real_tenants

    def _get_tenant(self, **kwargs):
        return self.kapi.tenants.find(**kwargs).id

    def _get_user(self, **kwargs):
        return self.kapi.users.find(**kwargs).id

    def _get_role(self, **kwargs):
        return self.kapi.roles.find(**kwargs).id

    def add_tenant(self, tenant_name, description=None, enabled=True, user=None, roles=None):
        tenant = self.kapi.tenants.create(tenant_name=tenant_name,
                                          description=description,
                                          enabled=enabled)
        if user and roles:
            user = self._get_user(name=user)
            for role in roles:
                role_id = self._get_role(name=role)
                tenant.add_user(user, role_id)
        return tenant.id

    def list_tenant(self):
        return [i.name for i in self._get_tenants()]

    def remove_tenant(self, tenant_name):
        tid = self._get_tenant(name=tenant_name)
        self.kapi.tenants.delete(tid)

    def start_vm(self, instance_name):
        logger.info(" Starting OpenStack instance %s" % instance_name)
        if self.is_vm_running(instance_name):
            return True

        instance = self._find_instance_by_name(instance_name)
        if self.is_vm_suspended(instance_name):
            instance.resume()
        elif self.is_vm_paused(instance_name):
            instance.unpause()
        else:
            instance.start()
        wait_for(lambda: self.is_vm_running(instance_name), message="start %s" % instance_name)
        return True

    def stop_vm(self, instance_name):
        logger.info(" Stopping OpenStack instance %s" % instance_name)
        if self.is_vm_stopped(instance_name):
            return True

        instance = self._find_instance_by_name(instance_name)
        instance.stop()
        wait_for(lambda: self.is_vm_stopped(instance_name), message="stop %s" % instance_name)
        return True

    def create_vm(self):
        raise NotImplementedError('create_vm not implemented.')

    def delete_vm(self, instance_name):
        logger.info(" Deleting OpenStack instance %s" % instance_name)
        instance = self._find_instance_by_name(instance_name)
        instance.delete()
        return self.does_vm_exist(instance_name)

    def restart_vm(self, instance_name):
        logger.info(" Restarting OpenStack instance %s" % instance_name)
        return self.stop_vm(instance_name) and self.start_vm(instance_name)

    def list_vm(self, **kwargs):
        instance_list = self._get_all_instances()
        return [instance.name for instance in instance_list]

    def list_template(self):
        template_list = self.api.images.list()
        return [template.name for template in template_list]

    def list_flavor(self):
        flavor_list = self.api.flavors.list()
        return [flavor.name for flavor in flavor_list]

    def list_volume(self):  # TODO: maybe names? Could not get it to work via API though ...
        volume_list = self.capi.volumes.list()
        return [volume.id for volume in volume_list]

    def list_network(self):
        network_list = self.api.networks.list()
        return [network.label for network in network_list]

    def info(self):
        return '%s %s' % (self.api.client.service_type, self.api.client.version)

    def disconnect(self):
        pass

    def vm_status(self, vm_name):
        return self._find_instance_by_name(vm_name).status

    def create_volume(self, size_gb, **kwargs):
        volume = self.capi.volumes.create(size_gb, **kwargs).id
        wait_for(lambda: self.capi.volumes.get(volume).status == "available", num_sec=60, delay=0.5)
        return volume

    def delete_volume(self, *ids, **kwargs):
        wait = kwargs.get("wait", True)
        timeout = kwargs.get("timeout", 180)
        for id in ids:
            self.capi.volumes.find(id=id).delete()
        if not wait:
            return
        # Wait for them
        wait_for(
            lambda: all(map(lambda id: not self.volume_exists(id), ids)),
            delay=0.5, num_sec=timeout)

    def volume_exists(self, id):
        try:
            self.capi.volumes.get(id)
            return True
        except cinder_exceptions.NotFound:
            return False

    def get_volume(self, id):
        return self.capi.volumes.get(id)

    @contextmanager
    def with_volume(self, *args, **kwargs):
        """Creates a context manager that creates a single volume with parameters defined via params
        and destroys it after exiting the context manager

        For arguments description, see the :py:meth:`OpenstackSystem.create_volume`.
        """
        volume = self.create_volume(*args, **kwargs)
        try:
            yield volume
        finally:
            self.delete_volume(volume)

    @contextmanager
    def with_volumes(self, *configurations, **kwargs):
        """Similar to :py:meth:`OpenstackSystem.with_volume`, but with multiple volumes.

        Args:
            *configurations: Can be either :py:class:`int` (taken as a disk size), or a tuple.
                If it is a tuple, then first element is disk size and second element a dictionary
                of kwargs passed to :py:meth:`OpenstackSystem.create_volume`. Can be 1-n tuple, it
                can cope with that.
        Keywords:
            n: How many copies of single configuration produce? Useful when you want to create eg.
                10 identical volumes, so you specify only one configuration and set n=10.

        Example:

            .. code-block:: python

               with mgmt.with_volumes(1, n=10) as (d0, d1, d2, d3, d4, d5, d6, d7, d8, d9):
                   pass  # provisions 10 identical 1G volumes

               with mgmt.with_volumes(1, 2) as (d0, d1):
                   pass  # d0 1G, d1 2G

               with mgmt.with_volumes((1, {}), (2, {})) as (d0, d1):
                   pass  # d0 1G, d1 2G same as before but you can see you can pass kwargs through

        """
        n = kwargs.pop("n", None)
        if n is None:
            pass  # Nothing to do
        elif n > 1 and len(configurations) == 1:
            configurations = n * configurations
        elif n != len(configurations):
            raise "n does not equal the length of configurations"
        # now n == len(configurations)
        volumes = []
        try:
            for configuration in configurations:
                if isinstance(configuration, int):
                    size, kwargs = configuration, {}
                elif len(configuration) == 1:
                    size, kwargs = configuration[0], {}
                elif len(configuration) == 2:
                    size, kwargs = configuration
                else:
                    size = configuration[0]
                    kwargs = configuration[1]
                volumes.append(self.create_volume(size, **kwargs))
            yield volumes
        finally:
            self.delete_volume(*volumes)

    def _get_instance_name(self, id):
        return self.api.servers.get(id).name

    def volume_attachments(self, volume_id):
        """Returns a dictionary of ``{instance: device}`` relationship of the volume."""
        volume = self.capi.volumes.get(volume_id)
        result = {}
        for attachment in volume.attachments:
            result[self._get_instance_name(attachment["server_id"])] = attachment["device"]
        return result

    def vm_creation_time(self, vm_name):
        instance = self._find_instance_by_name(vm_name)
        # Example vm.created: 2014-08-14T23:29:30Z
        create_time = datetime.strptime(instance.created, '%Y-%m-%dT%H:%M:%SZ')
        # create time is UTC, localize it, strip tzinfo
        return local_tz.fromutc(create_time).replace(tzinfo=None)

    def is_vm_running(self, vm_name):
        return self.vm_status(vm_name) in self.states['running']

    def is_vm_stopped(self, vm_name):
        return self.vm_status(vm_name) in self.states['stopped']

    def is_vm_suspended(self, vm_name):
        return self.vm_status(vm_name) in self.states['suspended']

    def is_vm_paused(self, vm_name):
        return self.vm_status(vm_name) in self.states['paused']

    def wait_vm_running(self, vm_name, num_sec=360):
        logger.info(" Waiting for OS instance %s to change status to ACTIVE" % vm_name)
        wait_for(self.is_vm_running, [vm_name], num_sec=num_sec)

    def wait_vm_stopped(self, vm_name, num_sec=360):
        logger.info(" Waiting for OS instance %s to change status to SHUTOFF" % vm_name)
        wait_for(self.is_vm_stopped, [vm_name], num_sec=num_sec)

    def wait_vm_suspended(self, vm_name, num_sec=720):
        logger.info(" Waiting for OS instance %s to change status to SUSPENDED" % vm_name)
        wait_for(self.is_vm_suspended, [vm_name], num_sec=num_sec)

    def wait_vm_paused(self, vm_name, num_sec=720):
        logger.info(" Waiting for OS instance %s to change status to PAUSED" % vm_name)
        wait_for(self.is_vm_paused, [vm_name], num_sec=num_sec)

    def suspend_vm(self, instance_name):
        logger.info(" Suspending OpenStack instance %s" % instance_name)
        if self.is_vm_suspended(instance_name):
            return True

        instance = self._find_instance_by_name(instance_name)
        instance.suspend()
        wait_for(lambda: self.is_vm_suspended(instance_name), message="suspend %s" % instance_name)

    def pause_vm(self, instance_name):
        logger.info(" Pausing OpenStack instance %s" % instance_name)
        if self.is_vm_paused(instance_name):
            return True

        instance = self._find_instance_by_name(instance_name)
        instance.pause()
        wait_for(lambda: self.is_vm_paused(instance_name), message="pause %s" % instance_name)

    def clone_vm(self, source_name, vm_name):
        raise NotImplementedError('clone_vm not implemented.')

    def deploy_template(self, template, *args, **kwargs):
        """ Deploys an OpenStack instance from a template.

        For all available args, see ``create`` method found here:
        http://docs.openstack.org/developer/python-novaclient/ref/v1_1/servers.html

        Most important args are listed below.

        Args:
            template: The name of the template to use.
            flavour_name: The name of the flavour to use.
            vm_name: A name to use for the vm.
            network_name: The name of the network if it is a multi network setup (Havanna).

        Note: If assign_floating_ip kwarg is present, then :py:meth:`OpenstackSystem.create_vm` will
            attempt to register a floating IP address from the pool specified in the arg.
        """
        power_on = kwargs.pop("power_on", True)
        nics = []
        timeout = kwargs.pop('timeout', 900)
        if 'flavour_name' not in kwargs:
            kwargs['flavour_name'] = 'm1.tiny'
        if 'vm_name' not in kwargs:
            kwargs['vm_name'] = 'new_instance_name'
        logger.info(" Deploying OpenStack template %s to instance %s (%s)" % (
            template, kwargs["vm_name"], kwargs["flavour_name"]))
        if len(self.list_network()) > 1:
            if 'network_name' not in kwargs:
                raise NetworkNameNotFound('Must select a network name')
            else:
                net_id = self.api.networks.find(label=kwargs['network_name']).id
                nics = [{'net-id': net_id}]

        image = self.api.images.find(name=template)
        flavour = self.api.flavors.find(name=kwargs['flavour_name'])
        instance = self.api.servers.create(kwargs['vm_name'], image, flavour, nics=nics,
                                           *args, **kwargs)
        self.wait_vm_running(kwargs['vm_name'], num_sec=timeout)
        if kwargs.get('floating_ip_pool', None):
            ip = self.api.floating_ips.create(kwargs['floating_ip_pool'])
            instance.add_floating_ip(ip)

        if power_on:
            self.start_vm(kwargs['vm_name'])

        return kwargs['vm_name']

    def _get_instance_networks(self, name):
        instance = self._find_instance_by_name(name)
        return instance._info['addresses']

    def current_ip_address(self, name):
        networks = self._get_instance_networks(name)
        for network_nics in networks.itervalues():
            for nic in network_nics:
                if nic['OS-EXT-IPS:type'] == 'floating':
                    return str(nic['addr'])

    def all_vms(self):
        result = []
        for vm in self._get_all_instances():
            ip = None
            for network_nics in vm._info["addresses"].itervalues():
                for nic in network_nics:
                    if nic['OS-EXT-IPS:type'] == 'floating':
                        ip = str(nic['addr'])
            result.append(VMInfo(
                vm.id,
                vm.name,
                vm.status,
                ip,
            ))
        return result

    def get_vm_name_from_ip(self, ip):
        # unfortunately it appears you cannot query for ip address from the sdk,
        #   unlike curling rest api which does work
        """ Gets the name of a vm from its IP.

        Args:
            ip: The ip address of the vm.
        Returns: The vm name for the corresponding IP."""

        instances = self._get_all_instances()

        for instance in instances:
            addr = self.get_ip_address(instance.name)
            if addr is not None and ip in addr:
                return str(instance.name)
        raise cfme_exc.VmNotFoundViaIP('The requested IP is not known as a VM')

    def get_ip_address(self, name, **kwargs):
        return self.current_ip_address(name)

    def _get_all_instances(self, filter_tenants=True):
        instances = self.api.servers.list(True, {'all_tenants': True})
        if filter_tenants:
            # Filter instances based on their tenant ID
            # needed for CFME 5.3 and higher
            tenants = self._get_tenants()
            ids = [tenant.id for tenant in tenants]
            instances = filter(lambda i: i.tenant_id in ids, instances)
        return instances

    def _get_all_templates(self):
        return self.api.images.list()

    def _find_instance_by_name(self, name):
        """
        OpenStack Nova Client does have a find method, but it doesn't
        allow the find method to be used on other tenants. The list()
        method is the only one that allows an all_tenants=True keyword
        """
        instances = self._get_all_instances()
        for instance in instances:
            if instance.name == name:
                return instance
        else:
            raise VMInstanceNotFound(name)

    def _find_template_by_name(self, name):
        templates = self._get_all_templates()
        for template in templates:
            if template.name == name:
                return template
        else:
            raise VMInstanceNotFound("template {}".format(name))

    def get_template_id(self, name):
        return self._find_template_by_name(name).id

    def does_vm_exist(self, name):
        try:
            self._find_instance_by_name(name)
            return True
        except Exception:
            return False

    def remove_host_from_cluster(self, hostname):
        raise NotImplementedError('remove_host_from_cluster not implemented')

    def get_first_floating_ip(self):
        try:
            self.api.floating_ips.create()
        except os_exceptions.NotFound:
            logger.error('No more Floating IPs available, will attempt to grab a free one')
        try:
            first_available_ip = (ip for ip in self.api.floating_ips.list()
                                  if ip.instance_id is None).next()
        except StopIteration:
            return None
        return first_available_ip.ip

    def mark_as_template(self, instance_name, **kwargs):
        """OpenStack marking as template is a little bit more complex than vSphere.

        We have to rename the instance, create a snapshot of the original name and then delete the
        instance."""
        logger.info("Marking {} as OpenStack template".format(instance_name))
        instance = self._find_instance_by_name(instance_name)
        original_name = instance.name
        copy_name = original_name + "_copytemplate"
        instance.update(copy_name)
        try:
            self.wait_vm_steady(copy_name)
            if not self.is_vm_stopped(copy_name):
                instance.stop()
                self.wait_vm_stopped(copy_name)
            uuid = instance.create_image(original_name)
            wait_for(lambda: self.api.images.get(uuid).status == "ACTIVE", num_sec=900, delay=5)
            instance.delete()
            wait_for(lambda: not self.does_vm_exist(copy_name), num_sec=180, delay=5)
        except Exception as e:
            logger.error(
                "Could not mark {} as a OpenStack template! ({})".format(instance_name, str(e)))
            instance.update(original_name)  # Clean up after ourselves
            raise

    def rename_vm(self, instance_name, new_name):
        instance = self._find_instance_by_name(instance_name)
        try:
            instance.update(new_name)
        except Exception as e:
            logger.exception(e)
            return instance_name
        else:
            return new_name

    def delete_template(self, template_name):
        template = self._find_template_by_name(template_name)
        template.delete()
        wait_for(lambda: not self.does_template_exist(template_name), num_sec=120, delay=10)
