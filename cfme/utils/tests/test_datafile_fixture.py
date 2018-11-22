# -*- coding: utf-8 -*-
import pytest

pytestmark = [pytest.mark.nondestructive, pytest.mark.skip_selenium]


def test_datafile_fixture_read(datafile):
    myfile = datafile("test_template")
    assert myfile.read() == "$replaceme"


def test_datafile_fixture_read_slash_path(datafile):
    myfile = datafile("/cfme/utils/test_datafile_fixture/test_template")
    assert myfile.read() == "$replaceme"


@pytest.mark.xfail("sys.version_info >= (3,0)", reason="python 3 string type missmatch")
def test_datafile_fixture_read_template(datafile):
    replacements = {"replaceme": "test!"}

    myfile = datafile("test_template", replacements=replacements)
    assert myfile.read() == replacements["replaceme"]
