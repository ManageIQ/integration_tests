# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import pytest

from utils.version import Version

GT = '>'
LT = '<'
EQ = '=='


@pytest.mark.parametrize(('v1', 'op', 'v2'), [
    ('1', LT, '2'),
    ('1', EQ, '1'),
    ('1.2.3.4', LT, '1.2.3.4.1'),
    ('1.2.3.4.1', GT, '1.2.3.4'),
    # (1.1, EQ, '1.1'),
    # (1, EQ, '1'),
    ('1.2.3.4-beta', LT, '1.2.3.4'),
    ('1.2.3.4-beta1', GT, '1.2.3.4-beta'),
    ('1.2.3.4-beta1.1', GT, '1.2.3.4-beta1'),
    ('1.2.3.4-alpha-nightly', GT, '1.2.3.4-alpha'),     # TODO: This one might be discussed
])
def test_version(v1, op, v2):
    v1 = Version(v1)
    v2 = Version(v2)
    if op == GT:
        assert v1 > v2
    elif op == LT:
        assert v1 < v2
    elif op == EQ:
        assert v1 == v2
