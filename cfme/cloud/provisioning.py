"""Provisioning-related forms and domain classes.

"""
from cfme.fixtures import pytest_selenium as sel
from cfme import web_ui as ui
from cfme.web_ui import toolbar
from cfme.web_ui.menu import nav
from cfme.web_ui import prov_form
from cfme.cloud import instance
assert instance

instances_by_provider_tree = ui.Tree("//ul[@class='dynatree-container']")


# Nav targets and helpers
def _nav_to_provision_form(context):

    toolbar.select('Lifecycle', 'Provision Instances')
    provider = context['provider']
    template_name = context['template_name']

    template = prov_form.template_select_form.template_table.find_row_by_cells({
        'Name': template_name,
        'Provider': provider.name
    })
    if template:
        sel.click(template)
        sel.click(prov_form.template_select_form.continue_button)
    else:
        # Better exception?
        raise ValueError('Navigation failed: Unable to find template "%s" for provider "%s"' %
            (template_name, provider.name))

nav.add_branch('clouds_instances_by_provider', {
    'clouds_provision_instances': _nav_to_provision_form
})
