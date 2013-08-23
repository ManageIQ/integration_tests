import pytest
from unittestzero import Assert

pytestmark = [
    pytest.mark.nondestructive,
    pytest.mark.skip_selenium
]

def test_datafile_fixture_read(datafile, request):
    myfile = datafile('test_template')
    Assert.equal(myfile.read(), '$replaceme')

def test_datafile_fixture_read_slash_path(datafile, request):
    myfile = datafile('/utils/test_datafile_fixture/test_template')
    Assert.equal(myfile.read(), '$replaceme')

def test_datafile_fixture_read_template(datafile, request):
    replacements = {
        'replaceme': 'test!'
    }

    myfile = datafile('test_template', replacements=replacements)
    Assert.equal(myfile.read(), replacements['replaceme'])
