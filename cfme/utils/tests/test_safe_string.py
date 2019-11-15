import pytest

from cfme.utils import safe_string


@pytest.mark.parametrize("source, result", [
    ('\u25cf', '&#9679;'),
    ('ěšč', '&#283;&#353;&#269;'),
    ('взорваться', '&#1074;&#1079;&#1086;&#1088;&#1074;&#1072;&#1090;&#1100;&#1089;&#1103;'),
    (4, '4')],
    ids=['ugly_nonunicode_character', 'latin_diacritics', 'cyrillic', 'non_string'])
def test_safe_string(source, result):
    assert safe_string(source) == result
