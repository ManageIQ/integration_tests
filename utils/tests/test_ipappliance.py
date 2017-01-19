# -*- coding: utf-8 -*-
from urlparse import urlparse
import pytest

from fixtures.pytest_store import store
from utils.appliance import IPAppliance
from utils.providers import setup_a_provider


def test_ipappliance_from_address():
    address = '1.2.3.4'
    ip_a = IPAppliance(address)
    assert ip_a.address == address
    assert ip_a.url == 'https://{}/'.format(address)


def test_ipappliance_from_url():
    address = '1.2.3.4'
    url = 'http://{}/'.format(address)
    ip_a = IPAppliance.from_url(url)
    assert ip_a.url == url
    assert ip_a.address == address


def test_ipappliance_use_baseurl():
    ip_a = IPAppliance()
    ip_a_parsed = urlparse(ip_a.url)
    env_parsed = urlparse(store.base_url)
    assert (ip_a_parsed.scheme, ip_a_parsed.netloc) == (env_parsed.scheme, env_parsed.netloc)
    assert ip_a.address in store.base_url


def test_ipappliance_managed_providers():
    ip_a = IPAppliance()
    provider = setup_a_provider(prov_class='infra')
    assert provider in ip_a.managed_providers


def test_context_hack(monkeypatch):

    ip_a = IPAppliance.from_url('http://127.0.0.2/')

    def not_good(*k):
        raise RuntimeError()
    monkeypatch.setattr(ip_a, '_screenshot_capture_at_context_leave', not_good)

    with pytest.raises(ValueError):
        with ip_a:
            raise ValueError("test")
