#!/usr/bin/env python2
# -*- coding: utf-8 -*-
""" SOAP wrapper for CFME.

Enables to operate Infrastructure objects. It has better VM provisioning code. OOP encapsulated.

Todo:
    * hook with mgmt_system.py to be able to do another operations with VMs that aren't possible
        through CFME SOAP
    * some caching to speed-up? Don't know how reliable that would be.

"""
from suds import WebFault
import db
import re

from utils.cfmedb import db_session_maker
from utils.log import logger
from utils.soap import soap_client
from utils.wait import wait_for


if "client" not in globals():
    client = soap_client()  # Ugly, but easiest to use :/


class MiqInfraObject(object):
    """ Base class for all infrastructure objects.

    Args:
        id: GUID or ID of the object, it depends on what does the particular SOAP function wants.

    """
    GETTER_FUNC = None
    TAG_PREFIX = None

    def __init__(self, id):
        self._id = str(id)
        assert self.GETTER_FUNC is not None, "You must specify GETTER_FUNC in the class!"
        assert self.TAG_PREFIX is not None, "You must specify TAG_PREFIX in the class!"

    @property
    def id(self):
        return self._id

    @property
    def object(self):
        """ Accesses SOAP object

        Accesses network.

        Todo:
            * cache?
        """
        return getattr(client.service, self.GETTER_FUNC)(self.id)

    @property
    def name(self):
        return str(self.object.name)

    @property
    def exists(self):
        try:
            self.object
            return True
        except WebFault:
            return False

    @property
    def ws_attributes(self):
        """ Processes object.ws_attributes into builtin types
        """
        result = {}
        for attribute in self.object.ws_attributes:
            if attribute.value is None:
                result[str(attribute.name)] = attribute.value
            elif attribute.data_type == "string" or attribute.data_type == "array_of_string":
                result[str(attribute.name)] = str(attribute.value)
            elif attribute.data_type == "integer":
                result[str(attribute.name)] = int(attribute.value)
            elif attribute.data_type == "boolean":
                result[str(attribute.name)] = str(attribute.value).lower().strip() == "true"
            else:   # TODO datetime
                result[str(attribute.name)] = str(attribute.value)
        return result

    @property
    def tags(self):
        """ Return tags as an array of :py:class:`MiqTag` objects.
        """
        fname = "%sGetTags" % self.TAG_PREFIX
        return [
            MiqTag(tag.category, tag.category_display_name, tag.tag_name, tag.tag_display_name,
                tag.tag_path, tag.display_name)
            for tag
            in getattr(client.service, fname)(self.id)
        ]

    def add_tag(self, tag):
        """ Add tag to the object

        Args:
            tag: Tuple with tag specification.
        """
        fname = "%sSetTag" % self.TAG_PREFIX
        if (isinstance(tag, tuple) or isinstance(tag, list)) and len(tag) == 2:
            return getattr(client.service, fname)(self.id, tag[0], tag[1])
        elif isinstance(tag, MiqTag):
            return getattr(client.service, fname)(self.id, tag.category, tag.tag_name)
        else:
            raise TypeError("Wrong type passed!")

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self.id))

    def __getattribute__(self, name):
        """ Delegates unknown calls to the received object
        """
        try:
            return super(MiqInfraObject, self).__getattribute__(name)
        except AttributeError as e:
            try:
                return getattr(self.object, name)
            except AttributeError:
                raise e


# Here comes rails (but in a good way)
class HasManyHosts(MiqInfraObject):
    @property
    def hosts(self):
        return [MiqHost(host.guid) for host in self.object.hosts]


class HasManyEMSs(MiqInfraObject):
    @property
    def emss(self):
        return [MiqEms(ems.guid) for ems in self.object.ext_management_systems]


class HasManyDatastores(MiqInfraObject):
    @property
    def datastores(self):
        return [MiqDatastore(store.id) for store in self.object.datastores]


class HasManyVMs(MiqInfraObject):
    @property
    def vms(self):
        return [MiqVM(vm.guid) for vm in self.object.vms]


class HasManyResourcePools(MiqInfraObject):
    @property
    def resource_pools(self):
        return [MiqResourcePool(rpool.id) for rpool in self.object.resource_pools]


class BelongsToProvider(MiqInfraObject):
    @property
    def provider(self):
        return MiqEms(self.object.ext_management_system.guid)


class BelongsToCluster(BelongsToProvider):
    @property
    def cluster(self):
        return MiqCluster(self.object.parent_cluster.id)


class MiqEms(HasManyDatastores, HasManyHosts, HasManyVMs, HasManyResourcePools):
    GETTER_FUNC = "FindEmsByGuid"
    TAG_PREFIX = "Ems"

    @property
    def port(self):
        return self.object.port

    @property
    def host_name(self):
        return self.object.hostname

    @property
    def ip_address(self):
        return self.object.ipaddress

    @property
    def clusters(self):
        return [MiqCluster(cluster.id) for cluster in self.object.clusters]

    @classmethod
    def find_by_name(cls, name):
        for ems in client.service.GetEmsList():
            if ems.name.strip().lower() == name.strip().lower():
                return cls(ems.guid)
        else:
            raise Exception("EMS with name %s not found!" % name)

    @classmethod
    def all(cls):
        return [cls(ems.guid) for ems in client.service.GetEmsList()]

    @property
    def direct_connection(self):
        """ Returns an API from mgmt_system.py targeted at this provider
        """
        # Find the credentials entry
        name = str(self.host_name)
        from utils.conf import cfme_data, credentials
        for prov_id, provider in cfme_data.get("management_systems", {}).iteritems():
            if provider.get("hostname", None) == name or provider.get("region", None) == name:
                credentials = credentials.get(provider["credentials"], {})
                provider_id = prov_id
                break
        else:
            raise NameError("Could not find provider %s in the credentials!" % name)
        ptype = str(self.type).lower()
        if ptype == "emsredhat":
            from utils.mgmt_system import RHEVMSystem
            return RHEVMSystem(self.host_name, credentials["username"], credentials["password"])
        elif ptype == "emsvmware":
            from utils.mgmt_system import VMWareSystem
            return VMWareSystem(self.host_name, credentials["username"], credentials["password"])
        elif ptype == "emsamazon":
            from utils.mgmt_system import EC2System
            return EC2System(**credentials)
        elif ptype == "emsopenstack":
            from utils.mgmt_system import OpenstackSystem
            credentials.update(
                {"auth_url": cfme_data["management_systems"][provider_id]["auth_url"]}
            )
            return OpenstackSystem(**credentials)
        else:
            TypeError("Unknown Provider type!")


class MiqVM(HasManyDatastores, BelongsToCluster):
    GETTER_FUNC = "FindVmByGuid"
    TAG_PREFIX = "Vm"

    @property
    def vendor(self):
        return self.object.vendor

    @property
    def description(self):
        return self.object.description

    @property
    def host(self):
        return MiqHost(self.object.host.guid)

    @property
    def is_powered_on(self):
        return self.object.power_state.strip().lower() == "on"

    @property
    def is_powered_off(self):
        return self.object.power_state.strip().lower() == "off"

    @property
    def is_suspended(self):
        return self.object.power_state.strip().lower() == "suspended"

    def power_on(self):
        return client.service.EVMSmartStart(self.id).result == "true"

    def power_off(self):
        return client.service.EVMSmartStop(self.id).result == "true"

    def suspend(self):
        return client.service.EVMSmartSuspend(self.id).result == "true"

    def delete(self):
        """ Delete the VM. Possible hook to mgmt_system.py, 'cause the delete is not always done
        properly.
        """
        name = str(self.name)
        if self.is_powered_on:
            if not self.power_off():
                raise Exception("Could not power off vm %s" % name)
            wait_for(lambda: self.is_powered_off, num_sec=60, delay=4, message="wait for power off")
        if not client.service.EVMDeleteVmByName(self.name):
            raise Exception("Could not delete vm %s" % name)
        wait_for(lambda: not self.exists, num_sec=60, delay=4, message="wait for VM removed")

    @classmethod
    def provision_from_template(cls, template_name, vm_name, cpus=1, memory=1024, vlan=None,
            first_name="Shadowman", last_name="RedHat", email="shadowm@n.redhat.com"):
        """ Provision VM from template.

        Works independently on the management system, tags appropriate VMDB objects to provision
        without problems.

        Args:
            template_name: Name of the template to use.
            vm_name: VM Name.
            cpus: How many CPUs should the VM have.
            memory: How much memory (in MB) should the VM have.
            vlan: Where to connect the VM. Obligatory for RHEV
            first_name: Name of the requestee
            last_name: Surname of the requestee
            email: Email of the requestee
        Returns: :py:class:`MiqVM` object with freshly provisioned VM.
        """
        db_session = db_session_maker(recreate=True)
        for vm in db_session.query(db.Vm.name, db.Vm.guid).filter(db.Vm.template == True):
            # Previous line is ok, if you change it to `is`, it won't work!
            if vm.name.strip() == template_name.strip():
                template_guid = vm.guid
                break
        else:
            raise Exception("Template %s not found!" % template_name)
        template = cls(template_guid)
        # Tag provider
        for tag in template.provider.tags:
            if tag.category == "prov_scope" and tag.tag_name == "all":
                break
        else:
            logger.info("Tagging provider %s" % template.provider.name)
            template.provider.add_tag(("prov_scope", "all"))
        # Tag all provider's hosts
        for host in template.provider.hosts:
            for tag in host.tags:
                if tag.category == "prov_scope" and tag.tag_name == "all":
                    break
            else:
                logger.info("Tagging host %s" % host.name)
                host.add_tag(("prov_scope", "all"))
        # Tag all provider's datastores
        for datastore in template.provider.datastores:
            if re.search(r"do.not", datastore.name.lower()) is not None:
                continue  # just for now to prevent do-not-use-datastore
                          # There is also another one that does not work but that shall be param'd
            for tag in datastore.tags:
                if tag.category == "prov_scope" and tag.tag_name == "all":
                    break
            else:
                logger.info("Tagging datastore %s" % datastore.name)
                datastore.add_tag(("prov_scope", "all"))
        # Create request
        template_fields = client.pipeoptions(dict(guid=template_guid))
        vm_fields = dict(
            number_of_cpu=cpus,
            vm_memory=memory,
            vm_name=vm_name
        )
        if vlan:    # RHEV-M requires this field
            vm_fields["vlan"] = vlan
        vm_fields = client.pipeoptions(vm_fields)
        requester = client.pipeoptions(dict(
            owner_first_name=first_name,
            owner_last_name=last_name,
            owner_email=email
        ))
        try:
            req_id = client.service.VmProvisionRequest(
                "1.1", template_fields, vm_fields, requester, "", ""
            ).id
        except WebFault as e:
            if "'Network/vLan' is required" in e.message:
                raise TypeError("You have to specify `vlan` parameter for this function! (RHEV-M?)")
            else:
                raise
        logger.info("Waiting for VM provisioning request approval")
        wait_for(
            lambda: client.service.GetVmProvisionRequest(req_id).approval_state == "approved",
            num_sec=60,
            delay=2,
            message="VM provision approval"
        )

        def check_whether_provisioning_finished():
            request = client.service.GetVmProvisionRequest(req_id)
            if request.status.lower().strip() == "error":
                raise Exception(request.message)    # change the exception class here
            return request.status.lower().strip() == "ok" and len(request.vms) > 0

        logger.info("Waiting for VM provisioning to be done")
        wait_for(check_whether_provisioning_finished, num_sec=300, delay=5, message="provisioning")
        vm_guid = client.service.GetVmProvisionRequest(req_id).vms[0].guid
        new_vm = MiqVM(client.service.FindVmByGuid(vm_guid).guid)
        # some basic sanity checks though they should always pass
        assert new_vm.name == vm_name
        assert new_vm.object.guid == vm_guid
        logger.info("VM has been provisioned")
        return new_vm


class MiqHost(HasManyDatastores, HasManyVMs, HasManyResourcePools, BelongsToCluster):
    GETTER_FUNC = "FindHostByGuid"
    TAG_PREFIX = "Host"

    @classmethod
    def all(cls):
        return [cls(host.guid) for host in client.service.EVMHostList()]


class MiqDatastore(HasManyHosts, HasManyEMSs):
    GETTER_FUNC = "FindDatastoreById"
    TAG_PREFIX = "Datastore"

    @classmethod
    def all(cls):
        return [cls(datastore.id) for datastore in client.service.EVMDatastoreList()]


class MiqCluster(
        HasManyDatastores, HasManyHosts, HasManyVMs, HasManyResourcePools, BelongsToProvider):
    GETTER_FUNC = "FindClusterById"
    TAG_PREFIX = "Cluster"

    @property
    def default_resource_pool(self):
        return MiqResourcePool(self.object.default_resource_pool.id)

    @classmethod
    def all(cls):
        return [cls(cluster.id) for cluster in client.service.EVMClusterList()]


class MiqResourcePool(HasManyHosts, HasManyEMSs):
    GETTER_FUNC = "FindResourcePoolById"
    TAG_PREFIX = "ResourcePool"

    @property
    def store_type(self):
        return str(self.object.store_type)

    @classmethod
    def all(cls):
        return [cls(rpool.id) for rpool in client.service.EVMResourcePoolList()]


class MiqTag(object):
    def __init__(self, category, category_dn, tag_name, tag_dname, tag_path, dn):
        self.category = category
        self.category_display_name = category_dn
        self.tag_name = tag_name
        self.tag_display_name = tag_dname
        self.tag_path = tag_path
        self.display_name = dn
