# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import pytest
import string
from utils.async import ResultsPool


def async_task(arg1, arg2):
    """Task to reverse argument. Asynchronously..."""
    return arg2, arg1


@pytest.mark.nondestructive
@pytest.mark.skip_selenium
def test_async():
    with ResultsPool(processes=3) as pool:
        for letter, digit in zip(string.letters[:3], string.digits[:3]):
            pool.apply_async(async_task, [letter, digit])

    assert pool.successful

    for result in pool.results:
        # Result should have reversed args, i.e.
        # digit, letter = async_task(letter, digit)
        digit, letter = result.get()
        assert digit in string.digits
        assert letter in string.letters
