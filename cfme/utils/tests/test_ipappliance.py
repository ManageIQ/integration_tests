# -*- coding: utf-8 -*-
from urlparse import urlparse
import pytest

from fixtures.pytest_store import store
from cfme.utils.appliance import IPAppliance, DummyAppliance


def test_ipappliance_from_hostname():
    hostname = '1.2.3.4'
    ip_a = IPAppliance(hostname=hostname)
    assert ip_a.hostname == hostname
    assert ip_a.url == 'https://{}/'.format(hostname)


def test_ipappliance_from_url():
    address = '1.2.3.4'
    url = 'http://{}/'.format(address)
    ip_a = IPAppliance.from_url(url)
    assert ip_a.url == url
    assert ip_a.hostname == address


# INVALID TEST CASE. You should always provide the hostname, unless you are an Appliance
# def test_ipappliance_use_baseurl(appliance):
#     if isinstance(appliance, DummyAppliance):
#         pytest.xfail("Dummy appliance cant provide base_url")
#     ip_a = IPAppliance()
#     ip_a_parsed = urlparse(ip_a.url)
#     env_parsed = urlparse(store.base_url)
#     assert (ip_a_parsed.scheme, ip_a_parsed.netloc) == (env_parsed.scheme, env_parsed.netloc)
#     assert ip_a.address in store.base_url


@pytest.mark.skipif(pytest.config.getoption('--dummy-appliance'),
                    reason="infra_provider cant support dummy instance")
def test_ipappliance_managed_providers(appliance, infra_provider):
    assert infra_provider in appliance.managed_known_providers


def test_context_hack(monkeypatch):

    ip_a = IPAppliance.from_url('http://127.0.0.2/')

    def not_good(*k):
        raise RuntimeError()
    monkeypatch.setattr(ip_a, '_screenshot_capture_at_context_leave', not_good)

    with pytest.raises(ValueError):
        with ip_a:
            raise ValueError("test")
