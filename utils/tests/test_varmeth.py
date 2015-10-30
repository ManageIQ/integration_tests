# -*- coding: utf-8 -*-
import pytest

from utils.varmeth import variable


class _TestClass(object):
    secret = 42

    @variable
    def meth1(self):
        return "default"

    @meth1.variant("a")
    def m1_va(self):
        return "a"

    @meth1.variant("b")
    def m1_vb(self):
        return "b"

    @variable()
    def meth2(self, a):
        return a

    @meth2.variant("a")
    def m2_va(self, a, b):
        return a, b

    @meth2.variant("b", "c")
    def m2_vb(self):
        return "b"

    @variable(alias="foobar")
    def can_reach_secret(self):
        return self.secret


@pytest.fixture(scope="function")
def o():
    return _TestClass()


def test_proper_self(o):
    assert o.can_reach_secret() == o.secret


def test_default_with_alias(o):
    assert o.can_reach_secret(method="foobar") == o.secret


def test_default_noparam(o):
    assert o.meth1() == "default"


@pytest.mark.parametrize("v", ["a", "b"])
def test_variants_noparam(o, v):
    assert o.meth1(method=v) == v


def test_raises_attrerror(o):
    with pytest.raises(AttributeError):
        o.meth1(method="I'm not here!")


def test_default_withparam(o):
    assert o.meth2(1) == 1


@pytest.mark.parametrize(
    ["v", "params", "returns"],
    [
        ("a", [1, 2], (1, 2)),
        ("b", [], "b"),
        ("c", [], "b")],
    ids=["a", "b", "c"])
def test_variants_withparam(o, v, params, returns):
    assert o.meth2(*params, method=v) == returns
