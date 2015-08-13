# -*- coding: utf-8 -*-
"""This module contains integration between pytest and :py:mod:`utils.wait`."""


def pytest_namespace():
    # Expose the waiting function in pytest
    from utils.wait import wait_for_decorator
    return {'wait_for': wait_for_decorator}
