from cfme.fixtures import pytest_selenium as sel
from cfme.ssui import ssui_links


def test_login():
    sel.ssui_force_navigate('Dashboard')


def test_ssui_links():
    ssui_links.go_to('My Services')
    ssui_links.go_to('My Requests')
    ssui_links.go_to('Service Catalog')
