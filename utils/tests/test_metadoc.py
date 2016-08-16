from __future__ import unicode_literals
import pytest

pytestmark = pytest.mark.meta(from_pytest='yep')


@pytest.mark.meta(from_decorator='seems to be')
def test_metadoc(meta):
    """This test function has a docstring!

    Metadata:

        valid_yaml: True
    """
    assert meta['from_docs']['valid_yaml']
    assert meta['from_pytest'] == 'yep'
    assert meta['from_decorator'] == 'seems to be'
