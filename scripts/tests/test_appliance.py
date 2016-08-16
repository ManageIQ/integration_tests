# -*- coding: utf-8 -*-
"""Tests for appliance.py script."""
from __future__ import unicode_literals
import pytest

from scripts import appliance


@pytest.mark.parametrize(
    ('input', 'output'), [
        ([], []),
        (['a', 'b', 'c'], ['a', 'b', 'c']),
        (['1', 'True', 'False', 'None'], [1, True, False, None]),
    ])
def test_process_args(input, output):
    assert appliance.process_args(input) == output
