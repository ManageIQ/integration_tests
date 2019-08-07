"""Helper functions related to the creation and destruction of virtual machines and instances
"""
from ssl import SSLError

import pytest
from novaclient.exceptions import OverLimit as OSOverLimit
from wrapanapi import AzureSystem
from wrapanapi.exceptions import VMInstanceNotCloned
from wrapanapi.systems.rhevm import Error as RHEVRequestError

from cfme.fixtures.pytest_store import store
from cfme.utils.log import logger
from cfme.utils.providers import get_crud


DEFAULT_SKIP = (OSOverLimit, RHEVRequestError, VMInstanceNotCloned, SSLError)


def deploy_template(provider_key, vm_name, template_name=None, timeout=900, **deploy_args):
    """
    Args:
        provider_key: Provider key on which the VM is to be created
        vm_name: Name of the VM to be deployed
        template_name: Name of the template that the VM is deployed from
        timeout: the timeout for template deploy

    Returns:
        wrapanapi.entities.Vm or wrapanapi.entities.Instance object
    """
    allow_skip = deploy_args.pop("allow_skip", ())
    if isinstance(allow_skip, dict):
        skip_exceptions = list(allow_skip.keys())
        callable_mapping = allow_skip
    elif isinstance(allow_skip, str) and allow_skip.lower() == "default":
        skip_exceptions = DEFAULT_SKIP
        callable_mapping = {}
    else:
        skip_exceptions = allow_skip
        callable_mapping = {}
    provider_crud = get_crud(provider_key)

    deploy_args.update(vm_name=vm_name)

    if template_name is None:
        try:
            template_name = provider_crud.data['templates']['small_template']['name']
        except KeyError:
            raise KeyError('small_template not defined for Provider {} in cfme_data.yaml'
                           .format(provider_key))

    deploy_args.update(template=template_name)

    deploy_args.update(provider_crud.deployment_helper(deploy_args))

    logger.info("Getting ready to deploy VM/instance %s from template %s on provider %s",
                vm_name, deploy_args['template'], provider_crud.data['name'])
    try:
        try:
            logger.debug("Deploy args: %s", deploy_args)
            if isinstance(provider_crud.mgmt, AzureSystem):
                template = provider_crud.mgmt.get_template(
                    template_name, container=deploy_args['template_container'])
            else:
                template = provider_crud.mgmt.get_template(template_name)
            vm = template.deploy(timeout=timeout, **deploy_args)
            logger.info("Provisioned VM/instance %r", vm)
        except Exception:
            logger.exception('Could not provisioning VM/instance %s', vm_name)
            for vm_to_cleanup in provider_crud.mgmt.find_vms(vm_name):
                try:
                    vm_to_cleanup.cleanup()
                except Exception:
                    logger.exception("Unable to clean up vm: %r", vm_to_cleanup.name)
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
    return vm
