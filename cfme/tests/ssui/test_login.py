from cfme.fixtures import pytest_selenium as sel


def test_login():
    sel.ssui_force_navigate('Dashboard')
