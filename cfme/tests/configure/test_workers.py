#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import pytest
from cfme.configure import configuration


@pytest.mark.nondestructive
@pytest.sel.go_to('dashboard')
def test_restart_workers():
    assert configuration.restart_workers("Generic Worker"), "Could not correctly restart workers!"
