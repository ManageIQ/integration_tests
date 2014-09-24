from utils.appliance import IPAppliance
from utils.conf import env


def test_ipappliance_from_address():
    address = '1.2.3.4'
    ip_a = IPAppliance(address)
    assert ip_a.address == address
    assert ip_a.url == 'https://%s/' % address


def test_ipappliance_from_url():
    address = '1.2.3.4'
    url = 'http://%s/' % address
    ip_a = IPAppliance.from_url(url)
    assert ip_a.url == url
    assert ip_a.address == address


def test_ipappliance_use_baseurl():
    ip_a = IPAppliance()
    assert ip_a.url == env['base_url']
    assert ip_a.address in env['base_url']
