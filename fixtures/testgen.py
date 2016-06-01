# -*- coding: utf-8 -*-
"""
Wrapper for metafunc.parametrize
It makes sure that parametrization using pytest_generate_tests is done through testgen.parametrize
which checks parameters and uncollects tests with no argvalues instead of skipping them like pytest
does by default.
"""
import pytest
from functools import partial
from utils import testgen


@pytest.mark.hookwrapper
def pytest_generate_tests(metafunc):
    # override metafunc.parametrize by testgen.parametrize but pass the original
    # metafunc.parametrize function further down the line so it can be eventually used
    metafunc.parametrize = partial(
        testgen.parametrize, metafunc, custom_parametrize_fn=metafunc.parametrize)
    yield
