#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import pytest
from cfme.configure import configuration
from cfme.web_ui import flash
from utils import conf


@pytest.fixture(scope="module", params=["default"])
def roles(request):
    param = request.param
    return conf.cfme_data['server_roles'][param]


@pytest.sel.go_to('dashboard')
def test_edit_server_roles(roles):
    roles = {name: True for name in roles}
    configuration.set_server_roles(**roles)
    flash.assert_no_errors()


@pytest.mark.usefixtures("maximized")
def test_verify_server_roles(roles):
    for role, is_enabled in configuration.get_server_roles().iteritems():
        if is_enabled:
            assert role in roles, "Role '%s' is selected but should not be" % role
        else:
            assert role not in roles, "Role '%s' is not selected but should be" % role
