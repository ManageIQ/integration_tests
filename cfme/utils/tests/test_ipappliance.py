import pytest

from cfme.utils.appliance import RegularAppliance


def test_ipappliance_from_hostname():
    hostname = '1.2.3.4'
    ip_a = RegularAppliance(hostname=hostname)
    assert ip_a.hostname == hostname
    assert ip_a.url == 'https://{}/'.format(hostname)


def test_ipappliance_from_url():
    address = '1.2.3.4'
    url = 'http://{}/'.format(address)
    ip_a = RegularAppliance.from_url(url)
    assert ip_a.url == url
    assert ip_a.hostname == address


@pytest.mark.skipif(lambda request: request.config.getoption('--dummy-appliance', default=False),
                    reason="infra_provider cant support dummy instance")
def test_ipappliance_managed_providers(appliance, infra_provider):
    assert infra_provider in appliance.managed_known_providers


@pytest.mark.skipif(lambda request: request.config.getoption('--dummy-appliance', default=False),
                    reason="infra_provider cant support dummy instance")
def test_context_hack(monkeypatch):

    ip_a = RegularAppliance.from_url('http://127.0.0.2/')

    def not_good(*k):
        raise RuntimeError()
    monkeypatch.setattr(ip_a, '_screenshot_capture_at_context_leave', not_good)

    with pytest.raises(ValueError):
        with ip_a:
            raise ValueError("test")
