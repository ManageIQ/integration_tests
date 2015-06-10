"""Helper functions related to the creation and destruction of virtual machines and instances
"""
import pytest

from cfme.cloud.provider import get_from_config as get_cloud_from_config
from cfme.infrastructure.provider import get_from_config as get_infra_from_config
from ovirtsdk.infrastructure.errors import RequestError as RHEVRequestError
from utils import conf
from utils.log import logger
from utils.mgmt_system import RHEVMSystem, VMWareSystem, EC2System, OpenstackSystem, SCVMMSystem
from utils.mgmt_system.exceptions import VMInstanceNotCloned
from utils.providers import infra_provider_type_map


def deploy_template(provider_key, vm_name, template_name=None, timeout=900, **deploy_args):

    allow_skip = deploy_args.pop("allow_skip", ())
    if isinstance(allow_skip, dict):
        skip_exceptions = allow_skip.keys()
        callable_mapping = allow_skip
    elif isinstance(allow_skip, basestring) and allow_skip.lower() == "default":
        skip_exceptions = (RHEVRequestError, VMInstanceNotCloned)
        callable_mapping = {}
    else:
        skip_exceptions = allow_skip
        callable_mapping = {}
    provider_type = conf.cfme_data.get('management_systems', {})[provider_key]['type']
    if provider_type in infra_provider_type_map:
        provider_crud = get_infra_from_config(provider_key)
    else:
        provider_crud = get_cloud_from_config(provider_key)

    mgmt = provider_crud.get_mgmt_system()
    data = provider_crud.get_yaml_data()

    deploy_args.update(vm_name=vm_name)
    if isinstance(mgmt, RHEVMSystem):
        if 'default_cluster' not in deploy_args:
            deploy_args.update(cluster=data['default_cluster'])
    elif isinstance(mgmt, VMWareSystem):
        if "allowed_datastores" not in deploy_args and "allowed_datastores" in data:
            deploy_args.update(allowed_datastores=data['allowed_datastores'])
    elif isinstance(mgmt, SCVMMSystem):
        if 'host_group' not in deploy_args:
            deploy_args.update(host_group=data.get("host_group", "All Hosts"))
    elif isinstance(mgmt, EC2System):
        pass
    elif isinstance(mgmt, OpenstackSystem):
        if ('network_name' not in deploy_args) and data.get('network'):
            deploy_args.update(network_name=data['network'])
    else:
        raise Exception("Unsupported provider type: %s" % mgmt.__class__.__name__)

    if template_name is None:
        template_name = data['small_template']

    logger.info("Getting ready to deploy VM/instance %s from template %s on provider %s" %
        (vm_name, template_name, data['name']))
    try:
        try:
            logger.debug("Deploy args: " + str(deploy_args))
            vm_name = mgmt.deploy_template(template_name, timeout=timeout, **deploy_args)
            logger.info("Provisioned VM/instance %s" % vm_name)  # instance ID in case of EC2
        except Exception as e:
            logger.error('Could not provisioning VM/instance %s (%s)', vm_name, e)
            try:
                logger.info("VM/Instance status: {}".format(mgmt.vm_status(vm_name)))
            except Exception as f:
                logger.error(
                    "Could not retrieve VM/Instance status: {}: {}".format(
                        type(f).__name__, str(f)))
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
                    'Could not destroy VM/instance {} ({}: {})'.format(
                        vm_name, type(f).__name__, str(f)))
            finally:
                raise e
    except skip_exceptions as e:
        e_c = type(e)
        if e_c in callable_mapping and not callable_mapping[e_c](e):
            raise
        pytest.skip("{}: {}".format(e_c.__name__, str(e)))
    return vm_name
