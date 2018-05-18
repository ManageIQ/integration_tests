"""Helper functions related to the creation and destruction of virtual machines and instances
"""
import pytest

import six
from cfme.utils.providers import get_crud
from cfme.fixtures.pytest_store import store
from novaclient.exceptions import OverLimit as OSOverLimit
from wrapanapi.rhevm import Error as RHEVRequestError
from ssl import SSLError
from cfme.utils.log import logger
from cfme.utils.mgmt_system import exceptions


DEFAULT_SKIP = (OSOverLimit, RHEVRequestError, exceptions.VMInstanceNotCloned, SSLError)


def deploy_template(provider_key, vm_name, template_name=None, timeout=900, **deploy_args):
    """
    Args:
        provider_key: Provider key on which the VM is to be created
        vm_name: Name of the VM to be deployed
        template_name: Name of the template that the VM is deployed from
        timeout: the timeout for template deploy
    """
    allow_skip = deploy_args.pop("allow_skip", ())
    if isinstance(allow_skip, dict):
        skip_exceptions = allow_skip.keys()
        callable_mapping = allow_skip
    elif isinstance(allow_skip, six.string_types) and allow_skip.lower() == "default":
        skip_exceptions = DEFAULT_SKIP
        callable_mapping = {}
    else:
        skip_exceptions = allow_skip
        callable_mapping = {}
    provider_crud = get_crud(provider_key)

    deploy_args.update(vm_name=vm_name)

    if template_name is None:
        try:
            deploy_args.update(template=provider_crud.data['templates']['small_template']['name'])
        except KeyError:
            raise KeyError('small_template not defined for Provider {} in cfme_data.yaml'
                           .format(provider_key))
    else:
        deploy_args.update(template=template_name)

    deploy_args.update(provider_crud.deployment_helper(deploy_args))

    logger.info("Getting ready to deploy VM/instance %s from template %s on provider %s",
        vm_name, deploy_args['template'], provider_crud.data['name'])
    try:
        try:
            logger.debug("Deploy args: %s", deploy_args)
            vm_name = provider_crud.mgmt.deploy_template(timeout=timeout, **deploy_args)
            logger.info("Provisioned VM/instance %s", vm_name)  # instance ID in case of EC2
        except Exception as e:
            logger.exception('Could not provisioning VM/instance %s (%s: %s)',
                vm_name, type(e).__name__, str(e))
            if vm_name in provider_crud.mgmt.list_vm():
                try:
                    provider_crud.mgmt.delete_vm(vm_name)
                except Exception:
                    logger.exception("Unable to clean up vm:", vm_name)
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
