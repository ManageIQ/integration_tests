# -*- coding: utf-8 -*-
import pytest
import random
from cfme.utils import conf
from cfme.utils import error

from cfme.infrastructure import host
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import testgen
from cfme.utils.blockers import BZ
from cfme.utils.update import update

pytestmark = [pytest.mark.tier(3)]

msgs = {
    'virtualcenter': 'Cannot complete login due to an incorrect user name or password.',
    'rhevm': 'Login failed due to a bad username or password.'
}


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [VMwareProvider, RHEVMProvider])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


def get_host_data_by_name(provider_key, host_name):
    for host_obj in conf.cfme_data.get('management_systems', {})[provider_key].get('hosts', []):
        if host_name == host_obj['name']:
            return host_obj
    return None


# Tests to automate BZ 1278904
def test_host_good_creds(appliance, request, setup_provider, provider):
    """
    Tests host credentialing  with good credentials
    """
    test_host = random.choice(provider.get_yaml_data()["hosts"])
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


@pytest.mark.meta(
    blockers=[BZ(1310910, unblock=lambda provider: provider.type != 'rhevm')]
)
def test_host_bad_creds(appliance, request, setup_provider, provider):
    """
    Tests host credentialing  with bad credentials
    """
    test_host = random.choice(provider.get_yaml_data()["hosts"])
    host_collection = appliance.collections.hosts
    host_obj = host_collection.instantiate(name=test_host.name, provider=provider)

    with error.expected(msgs[provider.type]):
        with update(host_obj, validate_credentials=True):
            host_obj.credentials = host.get_credentials_from_config('bad_credentials')
