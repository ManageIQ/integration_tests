"""Helper functions related to the creation and destruction of providers
"""

from utils.log import logger
from utils.mgmt_system import RHEVMSystem, EC2System, OpenstackSystem
from utils.wait import wait_for


def deploy_template(provider_crud, vm_name, template_name=None, timeout_in_minutes=15):
    mgmt = provider_crud.get_mgmt_system()
    data = provider_crud.get_yaml_data()
    deploy_args = {}
    deploy_args.update(vm_name=vm_name)
    if isinstance(mgmt, RHEVMSystem):
        deploy_args.update(cluster_name=data['default_cluster'])
    elif isinstance(mgmt, EC2System):
        deploy_args.update(instance_type=data['default_flavor'])
    elif isinstance(mgmt, OpenstackSystem):
        deploy_args.update(flavour_name=data['default_flavor'])
        deploy_args.update(assign_floating_ip=data['default_ip_pool'])

    if template_name is None:
        template_name = data['small_template']

    logger.info("Getting ready to deploy VM %s from template %s on provider %s" %
        (vm_name, template_name, data['name']))

    try:
        logger.debug("deploy args: " + str(deploy_args))
        mgmt.deploy_template(template_name, **deploy_args)
        wait_for(mgmt.does_vm_exist, [vm_name], num_sec=timeout_in_minutes * 60, delay=30)
    except Exception as e:
        logger.error('Could not provisioning VM %s (%s)', vm_name, e.message)
        logger.info('Attempting cleanup on VM %s', vm_name)
        try:
            if mgmt.does_vm_exist(vm_name):
                # Stop the vm first
                logger.warning('Destroying VM %s', vm_name)
                if mgmt.delete_vm(vm_name):
                    logger.info('VM %s destroyed', vm_name)
                else:
                    logger.error('Error destroying VM %s', vm_name)
        except Exception as f:
            logger.error('Could not destroy VM %s (%s)', vm_name, f.message)
        finally:
            raise e
