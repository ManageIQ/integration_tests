"""Provisioning-related forms and helper classes.

"""
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar
from cfme.web_ui.menu import nav
from cfme.web_ui import prov_form

import cfme.infrastructure.virtual_machines  # To ensure the infra_vm_and_templates is available
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
