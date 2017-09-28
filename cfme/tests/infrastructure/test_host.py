# -*- coding: utf-8 -*-
import pytest
import random

from cfme.base.credential import Credential
from cfme.common.host_views import HostsEditView
from cfme.common.provider_views import ProviderNodesView
from cfme.infrastructure.provider import InfraProvider
from cfme.utils import testgen
from cfme.utils.conf import credentials
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.infrastructure.provider.rhevm import RHEVMProvider

pytestmark = [pytest.mark.tier(3)]


def pytest_generate_tests(metafunc):
    # Filter out providers without multiple hosts defined
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [InfraProvider], required_fields=["hosts"])

    new_argvalues = []
    new_idlist = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        hosts = args['provider'].data.get('hosts', {})

        if len(hosts) < 2:
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


def navigate_and_select_quads(provider):
    """navigate to the hosts edit page and select all the quads on the first page

    Returns:
        view: the provider nodes view, quadicons already selected"""
    hosts_view = navigate_to(provider, 'ProviderNodes')
    assert hosts_view.is_displayed
    [h.check() for h in hosts_view.entities.get_all()]

    hosts_view.toolbar.configuration.item_select('Edit Selected items')
    edit_view = provider.create_view(HostsEditView)
    assert edit_view.is_displayed
    return edit_view


# Tests to automate BZ 1201092
def test_multiple_host_good_creds(setup_provider, provider):
    """  Tests multiple host credentialing  with good credentials """
    host = random.choice(provider.data["hosts"])
    creds = credentials[host['credentials']]
    cred = Credential(principal=creds.username, secret=creds.password)

    edit_view = navigate_and_select_quads(provider=provider)

    # Fill form with valid credentials for default endpoint and validate
    edit_view.endpoints.default.fill_with(cred.view_value_mapping)
    edit_view.validation_host.fill(host.name)
    edit_view.endpoints.default.validate_button.click()

    edit_view.flash.assert_no_error()
    edit_view.flash.assert_success_message('Credential validation was successful')

    # Save changes
    edit_view.save_button.click()
    view = provider.create_view(ProviderNodesView)
    view.flash.assert_no_error()
    view.flash.assert_success_message('Credentials/Settings saved successfully')


def test_multiple_host_bad_creds(setup_provider, provider):
    """    Tests multiple host credentialing with bad credentials """
    host = random.choice(provider.data["hosts"])
    bad_creds = credentials[host['credentials']]
    bad_creds.update({'password': 'bad_password'})
    cred = Credential(principal=bad_creds.username, secret=bad_creds.password)

    edit_view = navigate_and_select_quads(provider=provider)

    edit_view.endpoints.default.fill_with(cred.view_value_mapping)
    edit_view.validation_host.fill(host.name)
    edit_view.endpoints.default.validate_button.click()

    if provider.one_of(RHEVMProvider):
        msg = 'Login failed due to a bad username or password.'
    else:
        msg = 'Cannot complete login due to an incorrect user name or password.'
    edit_view.flash.assert_message(msg)

    edit_view.cancel_button.click()
