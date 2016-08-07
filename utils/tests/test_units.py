# -*- coding: utf-8 -*-
import pytest

from utils.units import Unit


@pytest.mark.parametrize(
    ('a', 'b'), [
        ('1 KB', '1024 Bytes'),
        ('1 KB', '1024 B'),
        ('231 KB', 231 * 1024),
        ('1 TB', '1024 GB'),
    ])
def test_compare_equal(a, b):
    assert Unit.parse(a) == b


@pytest.mark.parametrize(
    ('a', 'b'), [
        ('1 KB', '1025 Bytes'),
        ('1 KB', '10000 B'),
        ('231 KB', 231 * 1024 * 1024),
        ('1 TB', '1500 GB'),
    ])
def test_compare_lt(a, b):
    assert Unit.parse(a) < b
