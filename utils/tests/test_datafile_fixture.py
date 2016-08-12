# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import pytest

pytestmark = [
    pytest.mark.nondestructive,
    pytest.mark.skip_selenium
]


def test_datafile_fixture_read(datafile, request):
    myfile = datafile('test_template')
    assert myfile.read() == '$replaceme'


def test_datafile_fixture_read_slash_path(datafile, request):
    myfile = datafile('/utils/test_datafile_fixture/test_template')
    assert myfile.read() == '$replaceme'


def test_datafile_fixture_read_template(datafile, request):
    replacements = {
        'replaceme': 'test!'
    }

    myfile = datafile('test_template', replacements=replacements)
    assert myfile.read() == replacements['replaceme']
