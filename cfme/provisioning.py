from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.wait import wait_for


def do_vm_provisioning(appliance, template_name, provider, vm_name, provisioning_data, request,
                       num_sec=1500, wait=True, email="template_provisioner@example.com"):
    # generate_tests makes sure these have values
    vm = appliance.collections.infra_vms.instantiate(name=vm_name,
                                                     provider=provider,
                                                     template_name=template_name)
    note = ('template {} to vm {} on provider {}'.format(template_name, vm_name, provider.key))
    provisioning_data.update({
        'request': {
            'email': email,
            'first_name': 'Template',
            'last_name': 'Provisioner',
            'notes': note}})
    provisioning_data['template_name'] = template_name
    provisioning_data['provider_name'] = provider.name
    view = navigate_to(vm.parent, 'Provision', wait_for_view=0)
    view.form.fill_with(provisioning_data, on_change=view.form.submit_button)
    view.flash.assert_no_error()
    if not wait:
        return

    # Provision Re important in this test
    logger.info('Waiting for cfme provision request for vm %s', vm_name)
    request_description = 'Provision from [{}] to [{}]'.format(template_name, vm_name)
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui', num_sec=num_sec)
    assert provision_request.is_succeeded(method='ui'), "Provisioning failed: {}".format(
        provision_request.row.last_message.text)

    # Wait for the VM to appear on the provider backend before proceeding to ensure proper cleanup
    logger.info('Waiting for vm %s to appear on provider %s', vm_name, provider.key)
    wait_for(provider.mgmt.does_vm_exist, func_args=[vm_name], handle_exception=True, num_sec=600)
