"""Helper functions related to the creation and destruction of virtual machines and instances
"""
import pytest

from mgmtsystem.virtualcenter import VMWareSystem
from mgmtsystem.scvmm import SCVMMSystem
from mgmtsystem.azure import AzureSystem
from mgmtsystem.ec2 import EC2System
from mgmtsystem.google import GoogleCloudSystem
from mgmtsystem.openstack import OpenstackSystem
from mgmtsystem.rhevm import RHEVMSystem

from utils.providers import get_crud
from fixtures.pytest_store import store
from novaclient.exceptions import OverLimit as OSOverLimit
from ovirtsdk.infrastructure.errors import RequestError as RHEVRequestError
from ssl import SSLError
from utils.log import logger
from utils.mgmt_system import exceptions


def _vm_cleanup(mgmt, vm_name):
    """Separated to make the logic able to propagate the exceptions directly."""
    try:
        logger.info("VM/Instance status: %s", mgmt.vm_status(vm_name))
    except Exception as f:
        logger.error(
            "Could not retrieve VM/Instance status: %s: %s", type(f).__name__, str(f))
    logger.info('Attempting cleanup on VM/instance %s', vm_name)
    try:
        if mgmt.does_vm_exist(vm_name):
            # Stop the vm first
            logger.warning('Destroying VM/instance %s', vm_name)
            if mgmt.delete_vm(vm_name):
                logger.info('VM/instance %s destroyed', vm_name)
            else:
                logger.error('Error destroying VM/instance %s', vm_name)
    except Exception as f:
        logger.error(
            'Could not destroy VM/instance %s (%s: %s)', vm_name, type(f).__name__, str(f))


def deploy_template(provider_key, vm_name, template_name=None, timeout=900,
        **deploy_args):
    """
    Args:
        provider_key: Provider key on which the VM is to be created
        vm_name: Name of the VM to be deployed
        template_name: Name of the template that the VM is deployed from
    """
    allow_skip = deploy_args.pop("allow_skip", ())
    if isinstance(allow_skip, dict):
        skip_exceptions = allow_skip.keys()
        callable_mapping = allow_skip
    elif isinstance(allow_skip, basestring) and allow_skip.lower() == "default":
        skip_exceptions = (OSOverLimit, RHEVRequestError, exceptions.VMInstanceNotCloned, SSLError)
        callable_mapping = {}
    else:
        skip_exceptions = allow_skip
        callable_mapping = {}
    provider_crud = get_crud(provider_key)

    mgmt = provider_crud.get_mgmt_system()
    data = provider_crud.get_yaml_data()

    deploy_args.update(vm_name=vm_name)

    if template_name is None:
        try:
            deploy_args.update(template=data['small_template'])
        except KeyError:
            raise ValueError('small_template not defined for Provider {} in cfme_data.yaml'.format(
                provider_key))
    else:
        deploy_args.update(template=template_name)

    if isinstance(mgmt, RHEVMSystem):
        if 'default_cluster' not in deploy_args:
            deploy_args.update(cluster=data['default_cluster'])
    elif isinstance(mgmt, VMWareSystem):
        del deploy_args['username']
        del deploy_args['password']
        if "allowed_datastores" not in deploy_args and "allowed_datastores" in data:
            deploy_args.update(allowed_datastores=data['allowed_datastores'])
    elif isinstance(mgmt, SCVMMSystem):
        if 'host_group' not in deploy_args:
            deploy_args.update(host_group=data.get("host_group", "All Hosts"))
    elif isinstance(mgmt, EC2System):
        pass
    elif isinstance(mgmt, GoogleCloudSystem):
        pass
    elif isinstance(mgmt, AzureSystem):
        deploy_args.update(data['provisioning'])
    elif isinstance(mgmt, OpenstackSystem):
        if ('network_name' not in deploy_args) and data.get('network'):
            deploy_args.update(network_name=data['network'])
    else:
        raise Exception("Unsupported provider type: {}".format(type(mgmt).__name__))

    logger.info("Getting ready to deploy VM/instance %s from template %s on provider %s",
        vm_name, deploy_args['template'], data['name'])
    try:
        try:
            logger.debug("Deploy args: %s", deploy_args)
            vm_name = mgmt.deploy_template(timeout=timeout, **deploy_args)
            logger.info("Provisioned VM/instance %s", vm_name)  # instance ID in case of EC2
        except Exception as e:
            logger.error('Could not provisioning VM/instance %s (%s: %s)',
                vm_name, type(e).__name__, str(e))
            _vm_cleanup(mgmt, vm_name)
            raise
    except skip_exceptions as e:
        e_c = type(e)
        if e_c in callable_mapping and not callable_mapping[e_c](e):
            raise
        # Make it visible also in the log.
        store.write_line(
            "Skipping due to a provider error: {}: {}\n".format(e_c.__name__, str(e)), purple=True)
        logger.exception(e)
        pytest.skip("{}: {}".format(e_c.__name__, str(e)))
    return vm_name
