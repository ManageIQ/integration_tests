"""Provisioning-related forms and helper classes.

"""
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar
from cfme.web_ui.menu import nav
from cfme.web_ui import prov_form
from cfme.web_ui import flash, fill
from utils.log import logger
from utils.wait import wait_for
from utils import version

import cfme.infrastructure.virtual_machines  # To ensure the infra_vm_and_templates is available
from cfme.services import requests
assert cfme  # To prevent flake8 compalining


# Nav targets and helpers
def _nav_to_provision_form(context):
    toolbar.select('Lifecycle', 'Provision VMs')
    provider = context['provider']
    template_name = context['template_name']

    template = prov_form.template_select_form.template_table.find_row_by_cells({
        'Name': template_name,
        'Provider': provider.name
    })
    if template:
        sel.click(template)
        sel.click(prov_form.template_select_form.continue_button)
        return
    else:
        # Better exception?
        raise ValueError('Navigation failed: Unable to find template "%s" for provider "%s"' %
            (template_name, provider.key))

nav.add_branch('infra_vm_and_templates', {
    'infrastructure_provision_vms': _nav_to_provision_form
})


def cleanup_vm(vm_name, provider_key, provider_mgmt):
    try:
        logger.info('Cleaning up VM %s on provider %s' % (vm_name, provider_key))
        provider_mgmt.delete_vm(vm_name)
    except Exception as e:
        logger.warning('Failed to clean up VM {} on provider {}: {}'.format(vm_name,
                                                                            provider_key, str(e)))


def do_provisioning(template_name, provider_crud, vm_name, provisioning_data, request,
                    provider_mgmt, provider_key, smtp_test, num_sec=1500):
    # generate_tests makes sure these have values
    sel.force_navigate('infrastructure_provision_vms', context={
        'provider': provider_crud,
        'template_name': template_name,
    })

    note = ('template %s to vm %s on provider %s' %
        (template_name, vm_name, provider_crud.key))
    provisioning_data.update({
        'email': 'template_provisioner@example.com',
        'first_name': 'Template',
        'last_name': 'Provisioner',
        'notes': note,
    })

    fill(prov_form.provisioning_form, provisioning_data,
         action=prov_form.provisioning_form.submit_button)
    flash.assert_no_errors()

    # Wait for the VM to appear on the provider backend before proceeding to ensure proper cleanup
    logger.info('Waiting for vm %s to appear on provider %s', vm_name, provider_crud.key)
    wait_for(provider_mgmt.does_vm_exist, [vm_name], handle_exception=True, num_sec=600)

    # nav to requests page happens on successful provision
    logger.info('Waiting for cfme provision request for vm %s' % vm_name)
    row_description = 'Provision from [%s] to [%s]' % (template_name, vm_name)
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells],
                       fail_func=requests.reload, num_sec=num_sec, delay=20)
    assert row.last_message.text == version.pick(
        {version.LOWEST: 'VM Provisioned Successfully',
         "5.3": 'Vm Provisioned Successfully', })

    # Wait for e-mails to appear
    def verify():
        return (
            len(
                smtp_test.get_emails(
                    text_like="%%Your Virtual Machine Request was approved%%"
                )
            ) > 0
            and len(
                smtp_test.get_emails(
                    subject_like="Your virtual machine request has Completed - VM:%%%s" % vm_name
                )
            ) > 0
        )

    wait_for(verify, message="email receive check", delay=5)
