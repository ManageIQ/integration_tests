# -*- coding: utf-8 -*-
import random

import pytest

from cfme.common.host_views import HostDetailsView, HostEditView
from cfme.infrastructure import host
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import conf
from cfme.utils.blockers import BZ
from cfme.utils.update import update
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([InfraProvider], required_fields=['hosts'], scope='module')
]


msgs = {'virtualcenter': 'Login failed due to a bad username or password.',
        'rhevm': 'Login failed due to a bad username or password.',
        'scvmm': 'Check credentials. Remote error message: WinRM::WinRMAuthorizationError'}

# Credential type UI Element id and it's name in Authentication Table
credentials_type = {'remote_login': 'Remote Login Credentials',
                    'default': 'Default Credentials',
                    'web_services': 'Web Services Credentials',
                    }


def get_host_data_by_name(provider_key, host_name):
    for host_obj in conf.cfme_data.get('management_systems', {})[provider_key].get('hosts', []):
        if host_name == host_obj['name']:
            return host_obj
    return None


@pytest.mark.rhv1
@pytest.mark.meta(blockers=[
                  BZ(1584246, forced_streams=['5.8', '5.9'],
                     unblock=lambda provider: not provider.one_of(VMwareProvider)),
                  BZ(1584261, forced_streams=['5.8'],
                     unblock=lambda creds: creds == 'default'),
                  BZ(1584280, forced_streams=['5.9'],
                     unblock=lambda provider: not provider.one_of(RHEVMProvider))])
@pytest.mark.parametrize("creds", ["default", "remote_login", "web_services"],
                         ids=["default", "remote", "web"])
def test_host_good_creds(appliance, request, setup_provider, provider, creds):
    """
    Tests host credentialing  with good credentials

    Steps:
    1) Add Host credentials
    2) Validate + Save
    3) Verify Valid creds on Host Details page

    Metadata:
        test_flag: inventory
    """
    test_host = random.choice(provider.data["hosts"])
    host_data = get_host_data_by_name(provider.key, test_host.name)
    host_collection = appliance.collections.hosts
    host_obj = host_collection.instantiate(name=test_host.name, provider=provider)

    # Remove creds after test
    @request.addfinalizer
    def _host_remove_creds():
        with update(host_obj):
            host_obj.credentials = {creds: host.Host.Credential(
                principal="", secret="", verify_secret="")}

    with update(host_obj, validate_credentials=True):
        host_obj.credentials = {creds: host.get_credentials_from_config(host_data['credentials'])}
        # TODO Remove this workaround once our SCVMM env will work with common DNS
        if provider.one_of(SCVMMProvider):
            host_obj.hostname = host_data['ipaddress']

    def _refresh():
        view = appliance.browser.create_view(HostDetailsView)
        view.browser.refresh()
        try:
            creds_value = view.entities.summary('Authentication Status').get_text_of(
                credentials_type[creds])
        except NameError:
            return 'None'
        return creds_value

    wait_for(lambda: _refresh() == 'Valid', num_sec=180, delay=15,
             message='Waiting for \'{}\' state change'.format(credentials_type[creds]))


@pytest.mark.rhv3
@pytest.mark.meta(blockers=[
                  BZ(1584246, forced_streams=['5.8', '5.9'],
                     unblock=lambda provider: not provider.one_of(VMwareProvider)),
                  BZ(1584261, forced_streams=['5.8'],
                     unblock=lambda creds: creds == 'default'),
                  BZ(1584280, forced_streams=['5.9'],
                     unblock=lambda provider: not provider.one_of(RHEVMProvider))])
@pytest.mark.parametrize("creds", ["default", "remote_login", "web_services"],
                         ids=["default", "remote", "web"])
def test_host_bad_creds(appliance, request, setup_provider, provider, creds):
    """
    Tests host credentialing  with bad credentials

    Steps:
    1) Add Host credentials
    2) Validate + Save bad credentials
    3) Verify invalid creds on Host Details page

    Metadata:
        test_flag: inventory
    """
    test_host = random.choice(provider.data["hosts"])
    host_data = get_host_data_by_name(provider.key, test_host.name)
    host_collection = appliance.collections.hosts
    host_obj = host_collection.instantiate(name=test_host.name, provider=provider)
    flash_msg = msgs.get(provider.type)
    with pytest.raises(Exception, match=flash_msg):
        with update(host_obj, validate_credentials=True):
            host_obj.credentials = {creds: host.get_credentials_from_config('bad_credentials')}
            # TODO Remove this workaround once our SCVMM env will work with common DNS
            if provider.one_of(SCVMMProvider):
                host_obj.hostname = host_data['ipaddress']

    # Checking that we can save invalid creds and get proper credentials state in Host Details page
    edit_view = appliance.browser.create_view(HostEditView)
    edit_view.save_button.click()

    # Remove creds after test
    @request.addfinalizer
    def _host_remove_creds():
        with update(host_obj):
            host_obj.credentials = {creds: host.Host.Credential(
                principal="", secret="", verify_secret="")}

    def _refresh():
        view = appliance.browser.create_view(HostDetailsView)
        view.browser.refresh()
        try:
            creds_value = view.entities.summary('Authentication Status').get_text_of(
                credentials_type[creds])
        except NameError:
            return 'None'
        return creds_value

    wait_for(lambda: _refresh() in ['Error', 'Invalid'], num_sec=180, delay=15,
             message='Waiting for \'{}\' state change'.format(credentials_type[creds]))
