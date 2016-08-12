# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import pytest

from utils import safe_string


@pytest.mark.parametrize("source, result", [
    (u'\u25cf', '&#9679;'),
    (u'ěšč', '&#283;&#353;&#269;'),
    (u'взорваться', '&#1074;&#1079;&#1086;&#1088;&#1074;&#1072;&#1090;&#1100;&#1089;&#1103;'),
    (4, '4')],
    ids=['ugly_nonunicode_character', 'latin_diacritics', 'cyrillic', 'non_string'])
def test_safe_string(source, result):
    assert safe_string(source) == result
