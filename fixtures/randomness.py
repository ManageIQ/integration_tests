# -*- coding: utf-8 -*-
import fauxfactory
import pytest


@pytest.fixture  # IGNORE:E1101
def random_uuid_as_string():
    """Creates a random uuid and returns is as a string"""
    return fauxfactory.gen_uuid()


@pytest.fixture
def random_string():
    """Generate a random string for use in tests"""
    return fauxfactory.gen_alphanumeric(8)
