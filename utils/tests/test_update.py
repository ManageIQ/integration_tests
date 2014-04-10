#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import pytest
from utils.update import Updateable, update


class TestException(Exception):
    pass


class UpdateCls(Updateable):
    def __init__(self):
        self.a = None
        self.b = None

    def update(self, updates, fail=False):
        if "a" in updates:
            self.a = updates["a"]
        if "b" in updates:
            self.b = updates["b"]
        if fail:
            raise TestException()


@pytest.fixture(scope="function")
def update_obj():
    return UpdateCls()


def test_update_succeeds(update_obj):
    """Standard case - successful update

    Fields should be changed after jumping out of with.
    """
    with update(update_obj):
        update_obj.a = 2
        update_obj.b = 4
    assert update_obj.a == 2
    assert update_obj.b == 4


def test_update_fails(update_obj):
    """Fail case - update unsuccessful

    Fields should remain in previous state after jumping out of with.
    """
    try:
        with update(update_obj, fail=True):
            update_obj.a = 2
            update_obj.b = 4
        pytest.fail("update() somehow blocked the exception from passing through!")
    except TestException:
        pass
    assert update_obj.a is None
    assert update_obj.b is None
