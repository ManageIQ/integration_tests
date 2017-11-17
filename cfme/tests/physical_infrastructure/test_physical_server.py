# -*- coding: utf-8 -*-
import pytest
import random

from cfme.base.credential import Credential
from cfme.common.provider_views import ProviderNodesView
from cfme.infrastructure.provider import InfraProvider
from cfme.utils import testgen
from cfme.utils.conf import credentials
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.physical.physical_server import PhysicalServerCollection
from cfme.physical.physical_server import PhysicalServer
from cfme.physical.provider.lenovo import LenovoProvider

pytestmark = [pytest.mark.tier(3)]


def pytest_generate_tests(metafunc):
    # Filter out providers without multiple physical servers defined
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [InfraProvider], required_fields=["physical_servers"])

    new_argvalues = []
    new_idlist = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        physical_servers = args['provider'].data.get('physical_servers', {})

        if len(physical_servers) < 2:
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


def navigate_and_select_quads(physical_server):
    """navigate to the physical servers page and select all the quads on the first page

    Returns:
        view: the provider nodes view, quadicons already selected"""
    physical_servers_view = navigate_to(physical_server, 'All')
    assert physical_servers_view.is_displayed
    [physical_server.check() for physical_server in physical_servers_view.entities.get_all()]


def test_multiple_host_good_creds(setup_provider, provider):
    """  Tests multiple physical server credentialing  with good credentials """
    physical_server = random.choice(provider.data["physical_servers"])
    creds = credentials[physical_server['credentials']]
    cred = Credential(principal=creds.username, secret=creds.password)

    edit_view = navigate_and_select_quads(provider=provider)

    # Fill form with valid credentials for default endpoint and validate
    edit_view.endpoints.default.fill_with(cred.view_value_mapping)
    edit_view.validation_physical_server.fill(physical_server.name)
    edit_view.endpoints.default.validate_button.click()

    edit_view.flash.assert_no_error()
    edit_view.flash.assert_success_message('Credential validation was successful')

    # Save changes
    edit_view.save_button.click()
    view = provider.create_view(ProviderNodesView)
    view.flash.assert_no_error()
    view.flash.assert_success_message('Credentials/Settings saved successfully')


def test_multiple_physical_server_bad_creds(setup_provider, provider):
    """    Tests multiple host credentialing with bad credentials """
    physical_server = random.choice(provider.data["physical_servers"])
    bad_creds = credentials[host['credentials']]
    bad_creds.update({'password': 'bad_password'})
    cred = Credential(principal=bad_creds.username, secret=bad_creds.password)

    edit_view = navigate_and_select_quads(provider=provider)

    edit_view.endpoints.default.fill_with(cred.view_value_mapping)
    edit_view.validation_physical_server.fill(physical_server.name)
    edit_view.endpoints.default.validate_button.click()

    if provider.one_of(RHEVMProvider):
        msg = 'Login failed due to a bad username or password.'
    else:
        msg = 'Cannot complete login due to an incorrect user name or password.'
    edit_view.flash.assert_message(msg)

    edit_view.cancel_button.click()


