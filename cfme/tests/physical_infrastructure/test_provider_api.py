import pytest

from cfme.utils import testgen
from cfme.physical.provider.lenovo import LenovoProvider
from cfme.utils.wait import wait_for
from cfme.utils.generators import random_name

pytestmark = [pytest.mark.tier(3)]

pytest_generate_tests = testgen.generate([LenovoProvider], scope="class")

TIMEOUT = 50 # in seconds
DELAY = 10 # in seconds

NEW_NAME = random_name('physical')


@pytest.fixture(scope="class")
def provider_dict(provider):
    return {
      'type' : "ManageIQ::Providers::Lenovo::PhysicalInfraManager",
      'name' : provider.name,
      'hostname' : provider.endpoints['default'].hostname,
      'port' : provider.endpoints['default'].api_port,
      'credentials': {
        'password': provider.endpoints['default'].credentials.secret,
        'userid': provider.endpoints['default'].credentials.principal
      }
    }


@pytest.fixture(scope="class")
def api(appliance):
    return appliance.rest_api


def provider_exist(api, provider_href):
    try:
      api.get(provider_href)
      return api.response.ok
    except:
      return False


def is_provider_refreshed(api, provider_href):
    try:
      api.get(provider_href).last_refresh_date
      return True
    except:
      return False


def wait_for_provider_delete(api, provider_href):
    wait_for(
        lambda: not provider_exist(api, provider_href), num_sec=TIMEOUT, delay=DELAY
    )


def wait_for_provider_refresh(api, provider_href):
    wait_for(
        lambda: is_provider_refreshed(api, provider_href), num_sec=TIMEOUT, delay=DELAY
    )


@pytest.fixture(scope="class")
def providers_endpoint(appliance):
    return appliance.url + "api/providers"


def provider_href(api, name):
    return api.collections.providers.find_by(name=name)[0]['href']


def create(api, providers_endpoint, provider_dict):
    payload_create = provider_dict
    payload_create['action'] = 'create'
    api.post(providers_endpoint, **payload_create)
    assert api.response.ok
    provider_href = api.response.json()['results'][0]['href']
    assert api.get(provider_href)['name'] == provider_dict['name']


def edit(api, provider_dict):
    href = provider_href(api, provider_dict['name'])
    payload_edit = {
      'action':'edit',
      'name': NEW_NAME
    }

    api.post(href, **payload_edit)
    assert api.response.ok
    assert api.get(href)['name'] == NEW_NAME


def refresh(api):
    href = provider_href(api, NEW_NAME)
    payload_refresh = {
      'action': 'refresh'
    }
    api.post(href, **payload_refresh)

    wait_for_provider_refresh(api, href)

    assert is_provider_refreshed(api, href)


def delete(api):
    href = provider_href(api, NEW_NAME)

    payload_delete = {
      'action': 'delete'
    }

    api.post(href, **payload_delete)

    wait_for_provider_delete(api, href)

    assert not provider_exist(api, href)


def test_provider_crud(api, providers_endpoint, provider_dict):
    create(api, providers_endpoint, provider_dict)
    edit(api, provider_dict)
    refresh(api)
    delete(api)
