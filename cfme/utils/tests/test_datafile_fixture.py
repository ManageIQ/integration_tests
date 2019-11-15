import pytest

pytestmark = [
    pytest.mark.non_destructive,
]


def test_datafile_fixture_read(datafile):
    with datafile('test_template') as myfile:
        assert myfile.read() == '$replaceme'


def test_datafile_fixture_read_slash_path(datafile):
    with datafile('/cfme/utils/test_datafile_fixture/test_template') as myfile:
        assert myfile.read() == '$replaceme'


def test_datafile_fixture_read_template(datafile):
    replacements = {'replaceme': 'test!'}

    with datafile('test_template', replacements=replacements) as myfile:
        assert myfile.read() == replacements['replaceme']
