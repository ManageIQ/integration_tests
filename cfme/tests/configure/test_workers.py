# -*- coding: utf-8 -*-

import pytest
from cfme.configure import configuration


@pytest.mark.sauce
@pytest.mark.nondestructive
@pytest.sel.go_to('dashboard')
def test_restart_workers():
    assert (configuration.restart_workers("Generic Worker", wait_time_min=3),
            "Could not correctly restart workers!")
