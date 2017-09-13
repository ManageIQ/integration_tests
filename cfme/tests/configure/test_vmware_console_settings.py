# -*- coding: utf-8 -*-
import pytest

from cfme.configure.configuration import VMwareConsoleSupport
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.version import current_version


@pytest.mark.tier(3)
@pytest.mark.sauce
@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_vmware_console_support(appliance):
    """Tests that the VMware Console Support setting may be changed."""
    navigate_to(appliance.server, 'Server')

    console_type_loc = VMwareConsoleSupport.vmware_console_form.console_type
    old_vm_console_type = console_type_loc.first_selected_option_text
    assert old_vm_console_type, "The default VMware console type should not be empty"

    for new_vm_console_type in VMwareConsoleSupport.CONSOLE_TYPES:
        vmware_console_settings = VMwareConsoleSupport(
            appliance=appliance,
            console_type=new_vm_console_type
        )
        vmware_console_settings.update()

        cur_vm_console_type = console_type_loc.first_selected_option_text
        assert cur_vm_console_type == new_vm_console_type

    # Set back to original console type
    vmware_console_settings = VMwareConsoleSupport(
        appliance=appliance,
        console_type=old_vm_console_type
    )
    vmware_console_settings.update()
