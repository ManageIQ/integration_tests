# -*- coding: utf-8 -*-
from cfme.infrastructure.virtual_machines import Vm
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
from cfme.web_ui import flash


def do_vm_provisioning(appliance, template_name, provider, vm_name, provisioning_data, request,
                       smtp_test, num_sec=1500, wait=True):
    # generate_tests makes sure these have values
    vm = Vm(name=vm_name, provider=provider, template_name=template_name)
    note = ('template {} to vm {} on provider {}'.format(template_name, vm_name, provider.key))
    provisioning_data.update({
        'request': {
            'email': 'template_provisioner@example.com',
            'first_name': 'Template',
            'last_name': 'Provisioner',
            'notes': note}})
    view = navigate_to(vm, 'Provision')
    view.form.fill_with(provisioning_data, on_change=view.form.submit_button)
    flash.assert_no_errors()
    if not wait:
        return

    # Provision Re important in this test
    logger.info('Waiting for cfme provision request for vm %s', vm_name)
    request_description = 'Provision from [{}] to [{}]'.format(template_name, vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    assert provision_request.is_succeeded(method='ui'), \
        "Provisioning failed with the message {}".format(provision_request.row.last_message.text)

    # Wait for the VM to appear on the provider backend before proceeding to ensure proper cleanup
    logger.info('Waiting for vm %s to appear on provider %s', vm_name, provider.key)
    wait_for(provider.mgmt.does_vm_exist, [vm_name], handle_exception=True, num_sec=600)

    if smtp_test:
        # Wait for e-mails to appear
        def verify():
            approval = dict(subject_like="%%Your Virtual Machine configuration was Approved%%")
            expected_text = "Your virtual machine request has Completed - VM:%%{}".format(vm_name)
            return (
                len(smtp_test.get_emails(**approval)) > 0 and
                len(smtp_test.get_emails(subject_like=expected_text)) > 0
            )

        wait_for(verify, message="email receive check", delay=30)
