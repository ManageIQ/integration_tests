# -*- coding: utf-8 -*-
import pytest

from cfme.configure import about


@pytest.mark.tier(3)
@pytest.mark.sauce
def test_appliance_version(appliance):
    """Check version presented in UI against version retrieved directly from the machine.

    Version retrieved from appliance is in this format: 1.2.3.4
    Version in the UI is always: 1.2.3.4.20140505xyzblabla

    So we check whether the UI version starts with SSH version

    Polarion:
        assignee: None
        initialEstimate: None
    """
    ssh_version = str(appliance.version)
    ui_version = about.get_detail(about.VERSION, server=appliance.server)
    assert ui_version.startswith(ssh_version), "UI: {}, SSH: {}".format(ui_version, ssh_version)
