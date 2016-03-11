from cfme.fixtures import pytest_selenium as sel


def test_login():
    sel.force_navigate('dashboard')
