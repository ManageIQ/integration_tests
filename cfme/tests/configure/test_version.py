# -*- coding: utf-8 -*-
import pytest
from cfme.configure.about import product_assistance as about
from utils.ssh import SSHClient


@pytest.mark.sauce
def test_version():
    """Check version presented in UI against version retrieved directly from the machine.

    Version retrieved from appliance is in this format: 1.2.3.4
    Version in the UI is always: 1.2.3.4.20140505xyzblabla

    So we check whether the UI version starts with SSH version
    """
    pytest.sel.force_navigate("about")
    ssh_version = SSHClient().get_version().strip()
    ui_version = about.infoblock.text("Session Information", "Version").encode("utf-8").strip()
    assert ui_version.startswith(ssh_version), "UI: {}, SSH: {}".format(ui_version, ssh_version)
