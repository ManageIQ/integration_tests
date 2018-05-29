# -*- coding: utf-8 -*-
import random

import pytest

from cfme.infrastructure import host
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import conf
from cfme.utils.blockers import BZ
from cfme.utils.update import update

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([VMwareProvider, RHEVMProvider], scope='module')
]


msgs = {
    'virtualcenter': 'Cannot complete login due to an incorrect user name or password.',
    'rhevm': 'Login failed due to a bad username or password.'
}


def get_host_data_by_name(provider_key, host_name):
    for host_obj in conf.cfme_data.get('management_systems', {})[provider_key].get('hosts', []):
        if host_name == host_obj['name']:
            return host_obj
    return None


@pytest.mark.rhv1
# Tests to automate BZ 1278904
@pytest.mark.meta(blockers=[BZ(1516849,
                            forced_streams=['5.8', '5.9', 'upstream'],
                            unblock=lambda provider: not provider.one_of(RHEVMProvider))])
def test_host_good_creds(appliance, request, setup_provider, provider):
    """
    Tests host credentialing  with good credentials

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
            host_obj.credentials = host.Host.Credential(
                principal="", secret="", verify_secret="")

    with update(host_obj, validate_credentials=True):
        host_obj.credentials = host.get_credentials_from_config(host_data['credentials'])


@pytest.mark.rhv3
@pytest.mark.meta(blockers=[BZ(1516849,
                            forced_streams=['5.8', '5.9', 'upstream'],
                            unblock=lambda provider: not provider.one_of(RHEVMProvider))])
def test_host_bad_creds(appliance, request, setup_provider, provider):
    """
    Tests host credentialing  with bad credentials

    Metadata:
        test_flag: inventory
    """
    test_host = random.choice(provider.data["hosts"])
    host_collection = appliance.collections.hosts
    host_obj = host_collection.instantiate(name=test_host.name, provider=provider)

    with pytest.raises(Exception, match=msgs[provider.type]):
        with update(host_obj, validate_credentials=True):
            host_obj.credentials = host.get_credentials_from_config('bad_credentials')
